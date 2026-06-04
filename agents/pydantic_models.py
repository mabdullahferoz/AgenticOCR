from pydantic import BaseModel, Field
from typing import Optional

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