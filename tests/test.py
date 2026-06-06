import json
from agents.graph import agent_system

if __name__ == "__main__":
    print("[System Entry]: Launching Multi-Agent Workspace Verification...")
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