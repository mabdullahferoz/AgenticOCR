import os
from typing import Any
from google import genai
from google.genai import types

class APIKeyRotator:
    def __init__(self):
        self.api_keys = [
            os.getenv("GEMINI_API_KEY_1"),
            os.getenv("GEMINI_API_KEY_2"),
            os.getenv("GEMINI_API_KEY_3"),
            os.getenv("GEMINI_API_KEY_4"),
            os.getenv("GEMINI_API_KEY_5"),
        ]
        self.api_keys = [k for k in self.api_keys if k]
        
        if not self.api_keys:
            default_key = os.getenv("GEMINI_API_KEY")
            if default_key:
                self.api_keys = [default_key]
            else:
                raise ValueError("[ERROR] Critical Error: No Gemini API keys found in your environment configuration.")

        self.current_index = 0
        print(f"[API Guard]: Initialized key pool with {len(self.api_keys)} available keys.")
        self.client = genai.Client(api_key=self.api_keys[self.current_index])
        self.model_id = 'gemini-2.5-flash'

    def rotate_key(self):
        if len(self.api_keys) <= 1:
            print("[API Guard]: Warning! Quota hit but no alternative backup keys exist.")
            return False
            
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        new_key = self.api_keys[self.current_index]
        masked_key = f"...{new_key[-6:]}" if len(new_key) > 6 else "???"
        print(f"\n[API Guard ALERT]: Quota exhausted! Rotating to API Key Index [{self.current_index}] (Ends in: {masked_key})")
        
        self.client = genai.Client(api_key=new_key)
        return True

    def execute_with_retry(self, system_instruction: str, prompt_contents: Any, temp: float, response_schema: Any = None, mime_type: str = "text/plain"):
        max_attempts = len(self.api_keys)
        for attempt in range(max_attempts):
            try:
                config_args = {"system_instruction": system_instruction, "temperature": temp}
                if response_schema:
                    config_args["response_mime_type"] = mime_type
                    config_args["response_schema"] = response_schema

                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt_contents,
                    config=types.GenerateContentConfig(**config_args)
                )
                return response
            except Exception as e:
                error_str = str(e)
                error_code = getattr(e, "code", None)
                if error_code in (403, 429) or "RESOURCE_EXHAUSTED" in error_str or "PERMISSION_DENIED" in error_str or "403" in error_str or "429" in error_str:
                    print(f"[WARNING] [Attempt {attempt + 1}/{max_attempts} Failed]: API Error (Quota/Permission). Rotating key...")
                    if not self.rotate_key():
                        raise e
                else:
                    raise e
                    
        raise Exception("[ERROR] All API keys in the managed rotation pool have been exhausted.")

api_orchestrator = APIKeyRotator()