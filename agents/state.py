from typing import TypedDict, List, Dict, Any, Optional

class AgenticSystemState(TypedDict):
    user_input: str
    resolved_query: str
    query_constraints: Dict[str, Any]
    database_raw_hits: List[tuple]
    calculated_geometry: List[Dict[str, Any]]
    global_match_count: int
    final_execution_log: Dict[str, Any]
    token_usage: Dict[str, int]
    awaiting_confirmation: bool
    suggested_correction: Optional[str]