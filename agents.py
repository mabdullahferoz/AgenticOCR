import os
import sqlite3
import json
import difflib
from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END
from PIL import Image
import pytesseract
from tools.spatial_geometry import find_phrase_coordinates
from dotenv import load_dotenv
load_dotenv()

# Ensure Tesseract binary path is linked for Windows environment execution
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# =======================================================
# API KEY ROTATION & RESILIENCE MANAGER
# =======================================================

class APIKeyRotator:
    def __init__(self):
        # Load your pool of keys. You can load these from your .env file or a secure list.
        self.api_keys = [
            os.getenv("GEMINI_API_KEY_1"),
            os.getenv("GEMINI_API_KEY_2"),
            os.getenv("GEMINI_API_KEY_3"),
            os.getenv("GEMINI_API_KEY_4"),
            os.getenv("GEMINI_API_KEY_5"),
            # if more keys are created add them here as well
        ]
        # Filter out any None values in case some env variables aren't set yet
        self.api_keys = [k for k in self.api_keys if k]
        
        if not self.api_keys:
            # Fallback to the standard default env loader if specific ones aren't defined
            default_key = os.getenv("GEMINI_API_KEY")
            if default_key:
                self.api_keys = [default_key]
            else:
                raise ValueError("❌ Critical Error: No Gemini API keys found in your environment configuration.")

        self.current_index = 0
        print(f"[API Guard]: Initialized key pool with {len(self.api_keys)} available keys.")
        
        # Initialize the baseline active client
        self.client = genai.Client(api_key=self.api_keys[self.current_index])

    def rotate_key(self):
        """Swaps the active execution pointer to the next available API key in the pool."""
        if len(self.api_keys) <= 1:
            print("[API Guard]: Warning! Quota hit but no alternative backup keys exist in your pool layout.")
            return False
            
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        new_key = self.api_keys[self.current_index]
        
        # Obfuscate the print for security logs during display presentation
        masked_key = f"...{new_key[-6:]}" if len(new_key) > 6 else "???"
        print(f"\n🔄 [API Guard ALERT]: Quota exhausted! Rotating to API Key Index [{self.current_index}] (Ends in: {masked_key})")
        
        # Hot-reload the client instance dynamically in thread memory
        self.client = genai.Client(api_key=new_key)
        return True

    def execute_with_retry(self, system_instruction: str, prompt_contents: Any, temp: float, response_schema: Any = None, mime_type: str = "text/plain"):
        """
        Executes a call against Gemini. If a 429 rate limit hit is intercepted,
        it automatically rotates the client keys and tries again up to the maximum pool size.
        """
        max_attempts = len(self.api_keys)
        
        for attempt in range(max_attempts):
            try:
                # Build configuration parameters conditionally
                config_args = {"system_instruction": system_instruction, "temperature": temp}
                if response_schema:
                    config_args["response_mime_type"] = mime_type
                    config_args["response_schema"] = response_schema

                # Run the actual generation request
                response = self.client.models.generate_content(
                    model=MODEL_ID,
                    contents=prompt_contents,
                    config=types.GenerateContentConfig(**config_args)
                )
                return response
                
            except genai.errors.ClientError as e:
                # Inspect if the error payload explicitly points to an explicit 429 quota block
                if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                    print(f"⚠️ [Attempt {attempt + 1}/{max_attempts} Failed]: Hit rate limitation threshold.")
                    rotated_successfully = self.rotate_key()
                    if not rotated_successfully:
                        raise e # No more keys left to use, bubble up error safely
                else:
                    # Bubble up other authentic exceptions instantly (e.g., structural syntax errors)
                    raise e
                    
        raise genai.errors.ClientError("❌ All API keys in the managed rotation pool have been completely exhausted for this cycle.")

# Instantiate the pool wrapper globally inside your script scope
api_orchestrator = APIKeyRotator()

# =======================================================
# 1. INTENT REFINER SCHEMAS & STATE UTILITIES
# =======================================================

class IntentExtractor(BaseModel):
    search_phrase: str = Field(
        description="The core target word or text phrase to locate. Completely strip out conversational questions, surrounding quotes, and framing."
    )
    intent_type: str = Field(
        description="Must be exactly one of these three strings: 'LOCATION' (if seeking where it is or showing it), 'COUNT' (if asking how many times/frequency), or 'VERIFICATION' (if checking if it exists/is present)."
    )
    limit_occurrence: Optional[int] = Field(
        default=None, 
        description=(
            "CRITICAL: If the user requests a specific number of matches or instances (e.g., '5 instances', 'find 3 matches'), "
            "extract that exact integer value. If they explicitly say 'first occurrence', 'initial', or 'first instance' without "
            "another number, set this to 1. Otherwise, leave null."
        )
    )
    target_file: Optional[str] = Field(
        default=None, 
        description="If the user mentions a specific page/file parameter (e.g., 'page 95', 'inside page (12)'), extract the integer and format it strictly as 'page (X).png'. Otherwise, leave null."
    )

class AgenticSystemState(TypedDict):
    user_input: str
    resolved_query: str
    query_constraints: Dict[str, Any]
    database_raw_hits: List[tuple]
    calculated_geometry: List[Dict[str, Any]]  # Inter-agent layout link
    global_match_count: int                     # Inter-agent accumulator link
    final_execution_log: Dict[str, Any]
    token_usage: Dict[str, int]
    awaiting_confirmation: bool
    suggested_correction: Optional[str]

# Initialize Client
client = genai.Client()
MODEL_ID = 'gemini-2.5-flash'


# =======================================================
# 2. HELPER RETRIEVAL & FUZZY MATCH TOOLS
# =======================================================

def query_local_database(search_phrase: str, target_file: Optional[str] = None) -> str:
    """Queries database dynamically using exact matching rules and localized filename scopes."""
    conn = sqlite3.connect("spatial_rag.db")
    cursor = conn.cursor()
    
    if target_file:
        cursor.execute("""
            SELECT d.file_name, dp.page_number, dp.spatial_map 
            FROM document_pages dp
            JOIN documents d ON dp.document_id = d.id
            WHERE LOWER(dp.full_text) LIKE ? AND d.file_name = ?
        """, (f"%{search_phrase.lower()}%", target_file))
    else:
        cursor.execute("""
            SELECT d.file_name, dp.page_number, dp.spatial_map 
            FROM document_pages dp
            JOIN documents d ON dp.document_id = d.id
            WHERE LOWER(dp.full_text) LIKE ?
        """, (f"%{search_phrase.lower()}%",))
        
    matches = cursor.fetchall()
    conn.close()
    return json.dumps(matches)


def get_closest_database_match(failed_word: str) -> Optional[str]:
    """Scrapes unique words inside the database and isolates the closest alternative token via Edit Distance."""
    conn = sqlite3.connect("spatial_rag.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_text FROM document_pages")
    all_rows = cursor.fetchall()
    conn.close()
    
    vocabulary = set()
    for row in all_rows:
        if row[0]:
            words = [w.strip(".,;:!?()[]\"'").upper() for w in row[0].split()]
            vocabulary.update(words)
            
    closest_matches = difflib.get_close_matches(failed_word.upper(), list(vocabulary), n=1, cutoff=0.5)
    return closest_matches[0] if closest_matches else None


# =======================================================
# 3. AUTONOMOUS GEMINI GRAPH NODES
# =======================================================

def input_vision_agent(state: AgenticSystemState):
    """Multimodal Agent Node. Uses Gemini's vision capability to clean and extract target query strings."""
    image_path = state["user_input"]
    print(f"[Input Vision Agent]: Analyzing uploaded query image canvas: '{image_path}'")
    
    try:
        raw_image = Image.open(image_path)
        
        system_instruction = """
        You are an expert Computer Vision Inspection Agent. Your job is to analyze the text 
        written inside the provided query image snapshot. 
        Extract ONLY the primary word or text phrase that the user is trying to search for. 
        Completely ignore background layout noise, decorative borders, stray pixels, or handwriting markers.
        Return nothing but the clean, plain text phrase.
        """
        
        response = api_orchestrator.execute_with_retry(
            system_instruction=system_instruction,
            prompt_contents=[raw_image, "Extract the target search phrase from this image cleanly."],
            temp=0.0
        )
        
        resolved_query = response.text.strip().strip("'\"")
        print(f"[Input Vision Agent]: Gemini Brain resolved image text query to: '{resolved_query}'")
        return {"user_input": resolved_query, "resolved_query": resolved_query}
        
    except Exception as e:
        print(f"❌ [Input Vision Agent] Vision processing fallback to local OCR due to: {e}")
        try:
            img_gray = Image.open(image_path).convert('L')
            extracted_text = pytesseract.image_to_string(img_gray).strip()
            resolved_query = " ".join(extracted_text.split())
            return {"user_input": resolved_query, "resolved_query": resolved_query}
        except Exception as ocr_err:
            print(f"❌ Critical local OCR fallback failure: {ocr_err}")
            return {"user_input": "", "resolved_query": ""}
  

def autonomous_retrieval_agent(state: AgenticSystemState):
    user_input = state["user_input"].strip()
    
    # ----------------------------------------------------------------- 
    # SUB-ROUTINE A: INTERCEPT ACTIVE CONFIRMATION STEPS
    # -----------------------------------------------------------------
    if state.get("awaiting_confirmation"):
        print(f"[Retrieval Agent]: Active confirmation loop found. Evaluating response: '{user_input}'")
        
        if user_input.lower() in ["yes", "y", "yeah", "sure", "correct"]:
            confirmed_word = state["suggested_correction"]
            print(f"[Agent Correction]: User accepted prediction. Switching lookup parameter to: '{confirmed_word}'")
            
            tool_output = query_local_database(confirmed_word)
            raw_db_hits = json.loads(tool_output)
            
            return {
                "resolved_query": confirmed_word,
                "database_raw_hits": raw_db_hits,
                "query_constraints": {"intent_type": "LOCATION", "limit_occurrence": None, "target_file": None},
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "awaiting_confirmation": False,
                "suggested_correction": None
            }
        else:
            print("[Retrieval Agent]: User rejected spell matching prediction. Halting stream loop.")
            return {
                "final_execution_log": {"chatbot_markdown_response": "Search pipeline cancelled by user because the target term was not found."},
                "awaiting_confirmation": False,
                "suggested_correction": None,
                "database_raw_hits": []
            }
    # -----------------------------------------------------------------

    # -----------------------------------------------------------------
    # LOCAL CACHE / DIRECT MATCH BYPASS
    # -----------------------------------------------------------------
    is_conversational = any(mod in user_input.lower() for mod in ["first", "last", "count", "instances", "page", "show", "how many"])
    is_single_word = len(user_input.split()) == 1 and not is_conversational
    cleaned_token = user_input.strip("'\"")
    
    if is_single_word:
        print(f"[Local Bypass Optimizer]: Checking direct database hit for token: '{cleaned_token}'...")
        tool_output = query_local_database(cleaned_token)
        raw_db_hits = json.loads(tool_output)
        
        if raw_db_hits:
            print(f"[Local Bypass Optimizer]: Direct Match Found! Bypassing Gemini API call completely.")
            return {
                "resolved_query": cleaned_token,
                "database_raw_hits": raw_db_hits,
                "query_constraints": {"intent_type": "LOCATION", "limit_occurrence": None, "target_file": None},
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "awaiting_confirmation": False
            }
        else:
            print(f"[Local Bypass Optimizer]: No exact match for single token. Proceeding to fuzzy check...")
            suggestion = get_closest_database_match(cleaned_token)
            if suggestion:
                print(f"[Fuzzy Matcher Core]: Identified closest entry: '{suggestion}'. Prompting user...")
                return {
                    "resolved_query": cleaned_token,
                    "database_raw_hits": [],
                    "query_constraints": {"intent_type": "LOCATION", "limit_occurrence": None, "target_file": None},
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "awaiting_confirmation": True,
                    "suggested_correction": suggestion,
                    "final_execution_log": {
                        "status": "confirmation_required",
                        "chatbot_markdown_response": f"Could not find exact matches for '{cleaned_token}'. Did you mean **{suggestion}**?",
                        "suggested_word": suggestion
                    }
                }
    # -----------------------------------------------------------------

    print(f"[Retrieval Agent]: Refined Intent Parser running Gemini LLM analysis for phrase: '{user_input}'")

    system_instruction = """
    You are the absolute core analytical processor for a Document Spatial Intelligence Chatbot. 
    Your sole task is to dissect the user's conversational prompt and map it perfectly to the requested JSON schema.

    CRITICAL RULES FOR EXTRACTION:
    1. Isolate ONLY the core alphanumeric target text inside search_phrase. Strip all quotes and conversational filler.
    2. Map page limits (e.g., 'page 95') strictly to target_file formatted as 'page (X).png'.
    """

    # Replace the old raw generation call inside autonomous_retrieval_agent:
    response = api_orchestrator.execute_with_retry(
        system_instruction=system_instruction,
        prompt_contents=user_input,
        temp=0.0,
        response_schema=IntentExtractor,
        mime_type="application/json"
    )

    tokens = {
        "prompt_tokens": response.usage_metadata.prompt_token_count,
        "completion_tokens": response.usage_metadata.candidates_token_count,
        "total_tokens": response.usage_metadata.total_token_count
    }

    raw_db_hits = []
    resolved_query = user_input
    constraints = {"intent_type": "LOCATION", "limit_occurrence": None, "target_file": None}

    try:
        decision_json = json.loads(response.text)
        resolved_query = decision_json.get("search_phrase", "").strip("'\" ")
        constraints["intent_type"] = decision_json.get("intent_type", "LOCATION")
        constraints["limit_occurrence"] = decision_json.get("limit_occurrence")
        constraints["target_file"] = decision_json.get("target_file")
        
        print(f"[Intent Refiner Discovery] -> Type: {constraints['intent_type']} | Target: '{resolved_query}' | Scope: {constraints['target_file']}")
        
        tool_output = query_local_database(resolved_query, target_file=constraints["target_file"])
        raw_db_hits = json.loads(tool_output)
        
        if not raw_db_hits:
            suggestion = get_closest_database_match(resolved_query)
            if suggestion:
                return {
                    "resolved_query": resolved_query,
                    "database_raw_hits": [],
                    "query_constraints": constraints,
                    "token_usage": tokens,
                    "awaiting_confirmation": True,
                    "suggested_correction": suggestion,
                    "final_execution_log": {
                        "status": "confirmation_required",
                        "chatbot_markdown_response": f"Could not find exact matches for '{resolved_query}'. Did you mean **{suggestion}**?",
                        "suggested_word": suggestion
                    }
                }
        
    except Exception as e:
        print(f"❌ Intent Refiner parsing block error: {e}")

    return {
        "resolved_query": resolved_query,
        "database_raw_hits": raw_db_hits,
        "query_constraints": constraints,
        "token_usage": tokens,
        "awaiting_confirmation": False
    }


def autonomous_spatial_agent(state: AgenticSystemState):
    """Spatial Specialist Agent. Computes pixel boundaries while matching global limit rules."""
    raw_hits = state["database_raw_hits"]
    query = state["resolved_query"]
    constraints = state["query_constraints"]
    
    if not raw_hits:
        return {"calculated_geometry": [], "global_match_count": 0}

    print(f"[Spatial Agent]: LLM-backed boundary engine checking geometries for query: '{query}'...")
    
    spatial_logs = []
    total_occurrences = 0
    limit = constraints.get("limit_occurrence")
    
    for file_name, page_num, spatial_map_str in raw_hits:
        if limit and total_occurrences >= limit:
            break
            
        spatial_map = json.loads(spatial_map_str) if isinstance(spatial_map_str, str) else spatial_map_str
        phrase_boxes = find_phrase_coordinates(query, spatial_map)
        
        if phrase_boxes:
            if limit and limit > 0:
                remaining_budget = limit - total_occurrences
                phrase_boxes = phrase_boxes[:remaining_budget]
                
            if phrase_boxes:
                total_occurrences += len(phrase_boxes)
                spatial_logs.append({
                    "file_name": file_name,
                    "page": page_num,
                    "occurrences_found": len(phrase_boxes),
                    "tblr_coordinates": phrase_boxes
                })

    return {
        "calculated_geometry": spatial_logs,
        "global_match_count": total_occurrences
    }


def conversational_synthesis_agent(state: AgenticSystemState):
    """Final Synthesis Spokesman Node. Formats execution records into natural Markdown chat blocks."""
    user_original_prompt = state["user_input"]
    resolved_query = state["resolved_query"]
    constraints = state["query_constraints"]
    tokens = state.get("token_usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    
    geometry_facts = state.get("calculated_geometry", [])
    total_matches = state.get("global_match_count", 0)
    
    print("[Synthesis Agent]: Compiling telemetry metrics and formatting final conversational report...")
    
    system_instruction = """
    You are the polished user-facing Spokesman for a Document Spatial Intelligence Agentic System. 
    You will receive a collection of structured metrics (database outputs, bounding boxes, and token numbers).
    Your job is to look at the user's original prompt and compose an elegant Markdown chat response.
    
    STYLING INSTRUCTIONS:
    - If intent is 'COUNT', state the occurrence metrics conversationally.
    - If intent is 'VERIFICATION', respond with a clear confirmation statement.
    - If coordinates are present, format them cleanly using clean Markdown layout tables or lists.
    - Always wrap structural file names like 'page (X).png' in clean bold markers.
    """
    
    context_payload = f"""
    User's Original Chat Input: {user_original_prompt}
    Target Isolated Token: {resolved_query}
    Intent Classification: {constraints.get('intent_type')}
    Total Global Occurrences Discovered: {total_matches}
    Calculated Layout Geometry Arrays: {json.dumps(geometry_facts)}
    System Tokens Consumed: {json.dumps(tokens)}
    """
    
    # Replace the old raw generation call inside conversational_synthesis_agent:
    response = api_orchestrator.execute_with_retry(
        system_instruction=system_instruction,
        prompt_contents=context_payload,
        temp=1.0
    )
    
    final_report = {
        "chatbot_markdown_response": response.text,
        "telemetry": {
            "total_matches_found": total_matches,
            "tokens_consumed": tokens
        },
        "raw_geometry_manifest": geometry_facts
    }
    return {"final_execution_log": final_report}


# =======================================================
# 4. COMPILING THE CONFIGURABLE STATE ENGINE GRAPH
# =======================================================

def route_input_origin(state: AgenticSystemState):
    user_input = state["user_input"]
    if isinstance(user_input, str) and user_input.lower().endswith(('.png', '.jpg', '.jpeg')):
        return "vision_path"
    return "retrieval_path"


def route_post_retrieval(state: AgenticSystemState):
    if state.get("awaiting_confirmation"):
        return "halt"
    return "process_spatial_math"


workflow = StateGraph(AgenticSystemState)

workflow.add_node("InputVisionAgent", input_vision_agent)
workflow.add_node("RetrievalAgent", autonomous_retrieval_agent)
workflow.add_node("SpatialAgent", autonomous_spatial_agent)
workflow.add_node("SynthesisAgent", conversational_synthesis_agent)

workflow.set_conditional_entry_point(
    route_input_origin,
    {
        "vision_path": "InputVisionAgent",
        "retrieval_path": "RetrievalAgent"
    }
)

workflow.add_edge("InputVisionAgent", "RetrievalAgent")
workflow.add_conditional_edges(
    "RetrievalAgent",
    route_post_retrieval,
    {
        "halt": END,
        "process_spatial_math": "SpatialAgent"
    }
)
workflow.add_edge("SpatialAgent", "SynthesisAgent")
workflow.add_edge("SynthesisAgent", END)

agent_system = workflow.compile()


# =======================================================
# 5. TESTING EXECUTIONS RUNNER
# =======================================================
if __name__ == "__main__":
    state = {
        "user_input": "find the last instance of the word 'TOTAL'",
        "resolved_query": "",
        "query_constraints": {},
        "database_raw_hits": [],
        "calculated_geometry": [],
        "global_match_count": 0,
        "final_execution_log": {},
        "awaiting_confirmation": False,
        "suggested_correction": None
    }    
    
    output = agent_system.invoke(state)
    print("\n--- CHATBOT FINAL RENDER VIEW ---")
    print(output["final_execution_log"]["chatbot_markdown_response"])