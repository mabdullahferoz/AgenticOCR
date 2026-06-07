import os
import sqlite3
import json
from PIL import Image
import easyocr
from config.api_manager import api_orchestrator
from tools.spatial_geometry import find_phrase_coordinates
from agents.state import AgenticSystemState
from agents.pydantic_models import IntentExtractor

# Compute path to root DB file relative to this folder position
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "spatial_rag.db")

def query_local_database(search_phrase: str, target_file: str = None) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if target_file:
        cursor.execute("""
            SELECT d.file_name, dp.page_number, dp.page_file_name, dp.spatial_map 
            FROM document_pages dp
            JOIN documents d ON dp.document_id = d.id
            WHERE LOWER(dp.full_text) LIKE ? AND d.file_name = ?
        """, (f"%{search_phrase.lower()}%", target_file))
    else:
        cursor.execute("""
            SELECT d.file_name, dp.page_number, dp.page_file_name, dp.spatial_map 
            FROM document_pages dp
            JOIN documents d ON dp.document_id = d.id
            WHERE LOWER(dp.full_text) LIKE ?
        """, (f"%{search_phrase.lower()}%",))
    matches = cursor.fetchall()
    conn.close()
    return json.dumps(matches)

def input_vision_agent(state: AgenticSystemState):
    image_path = state["user_input"]
    print(f"[Input Vision Agent]: Analyzing uploaded query image canvas: '{image_path}'")
    try:
        raw_image = Image.open(image_path)
        system_instruction = """
        You are an expert Computer Vision Inspection Agent. Your job is to analyze the text written inside the provided query image snapshot. 
        Extract ONLY the primary word or text phrase that the user is trying to search for. Completely ignore noise.
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
        print(f"[ERROR] [Input Vision Agent] Vision processing fallback to local OCR due to: {e}")
        try:
            reader = easyocr.Reader(['en'], gpu=False)
            result = reader.readtext(image_path)
            
            texts = [text for (_, text, _) in result if text.strip()]
                
            resolved = " ".join(texts)
            return {"user_input": resolved, "resolved_query": resolved}
        except Exception as ocr_err:
            print(f"[ERROR] Critical local OCR fallback failure: {ocr_err}")
            return {"user_input": "", "resolved_query": ""}

def autonomous_retrieval_agent(state: AgenticSystemState):
    user_input = state["user_input"].strip()
    
    # confirmation step check
    if state.get("awaiting_confirmation"):
        print(f"[Retrieval Agent]: Active confirmation loop found. Evaluating response: '{user_input}'")
        if user_input.lower() in ["yes", "y", "yeah", "sure", "correct"]:
            confirmed_word = state["suggested_correction"]
            print(f"[Agent Correction]: User accepted prediction. Switching lookup parameter to: '{confirmed_word}'")
            tool_output = query_local_database(confirmed_word)
            return {
                "resolved_query": confirmed_word, "database_raw_hits": json.loads(tool_output),
                "query_constraints": {"intent_type": "LOCATION", "limit_occurrence": None, "target_file": None},
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "awaiting_confirmation": False, "suggested_correction": None
            }
        else:
            print("[Retrieval Agent]: User rejected spell matching prediction. Halting stream loop.")
            return {
                "final_execution_log": {"chatbot_markdown_response": "Search pipeline cancelled by user because the target term was not found."},
                "awaiting_confirmation": False, "suggested_correction": None, "database_raw_hits": []
            }

    # bypass check
    is_conversational = any(mod in user_input.lower() for mod in ["first", "last", "count", "instances", "page", "show", "how many"])
    is_single_word = len(user_input.split()) == 1 and not is_conversational
    cleaned_token = user_input.strip("'\"")
    
    if is_single_word:
        print(f"[Local Bypass Optimizer]: Checking direct database hit for token: '{cleaned_token}'...")
        raw_hits = json.loads(query_local_database(cleaned_token))
        if raw_hits:
            print(f"[Local Bypass Optimizer]: Direct Match Found! Bypassing Gemini API call completely.")
            return {
                "resolved_query": cleaned_token, "database_raw_hits": raw_hits,
                "query_constraints": {"intent_type": "LOCATION", "limit_occurrence": None, "target_file": None},
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "awaiting_confirmation": False
            }
        else:
            print(f"[Local Bypass Optimizer]: No exact match for single token. Proceeding to fuzzy check...")
            from data.ingest_dataset import get_closest_database_match
            suggestion = get_closest_database_match(cleaned_token)
            if suggestion:
                print(f"[Fuzzy Matcher Core]: Identified closest entry: '{suggestion}'. Prompting user...")
                return {
                    "resolved_query": cleaned_token, "database_raw_hits": [],
                    "query_constraints": {"intent_type": "LOCATION", "limit_occurrence": None, "target_file": None},
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "awaiting_confirmation": True, "suggested_correction": suggestion,
                    "final_execution_log": {
                        "status": "confirmation_required",
                        "chatbot_markdown_response": f"Could not find exact matches for '{cleaned_token}'. Did you mean **{suggestion}**?",
                        "suggested_word": suggestion
                    }
                }

    print(f"[Retrieval Agent]: Refined Intent Parser running Gemini LLM analysis for phrase: '{user_input}'")
    system_instruction = """
    You are the absolute core analytical processor for a Document Spatial Intelligence Chatbot. 
    Your sole task is to dissect the user's conversational prompt and map it perfectly to the requested JSON schema.
    CRITICAL RULES FOR EXTRACTION:
    1. Isolate ONLY the core alphanumeric target text inside search_phrase. Strip all quotes and conversational filler.
    2. Map page limits (e.g., 'page 95') strictly to target_file formatted as 'page (X).png'.
    """
    response = api_orchestrator.execute_with_retry(
        system_instruction=system_instruction, prompt_contents=user_input, temp=0.0,
        response_schema=IntentExtractor, mime_type="application/json"
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
        constraints["occurrence_position"] = decision_json.get("occurrence_position", "all")
        
        print(f"[Intent Refiner Discovery] -> Type: {constraints['intent_type']} | Target: '{resolved_query}' | Scope: {constraints['target_file']}")
        raw_db_hits = json.loads(query_local_database(resolved_query, target_file=constraints["target_file"]))
        
        if not raw_db_hits:
            from data.ingest_dataset import get_closest_database_match
            suggestion = get_closest_database_match(resolved_query)
            if suggestion:
                return {
                    "resolved_query": resolved_query, "database_raw_hits": [], "query_constraints": constraints,
                    "token_usage": tokens, "awaiting_confirmation": True, "suggested_correction": suggestion,
                    "final_execution_log": {
                        "status": "confirmation_required",
                        "chatbot_markdown_response": f"Could not find exact matches for '{resolved_query}'. Did you mean **{suggestion}**?",
                        "suggested_word": suggestion
                    }
                }
    except Exception as e:
        print(f"[ERROR] Intent Refiner parsing block error: {e}")

    return {
        "resolved_query": resolved_query, "database_raw_hits": raw_db_hits,
        "query_constraints": constraints, "token_usage": tokens, "awaiting_confirmation": False
    }

def autonomous_spatial_agent(state: AgenticSystemState):
    raw_hits = state["database_raw_hits"]
    query = state["resolved_query"]
    constraints = state["query_constraints"]
    
    if not raw_hits:
        return {"calculated_geometry": [], "global_match_count": 0}

    print(f"[Spatial Agent]: LLM-backed boundary engine checking geometries for query: '{query}'...")
    spatial_logs = []
    total_occurrences = 0
    limit = constraints.get("limit_occurrence")
    position = constraints.get("occurrence_position", "all")
    
    for file_name, page_num, page_file_name, spatial_map_str in raw_hits:
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
                    "file_name": file_name, "page": page_num, "page_file_name": page_file_name,
                    "occurrences_found": len(phrase_boxes), "tblr_coordinates": phrase_boxes
                })

    if position == "last" and spatial_logs:
        last_log = spatial_logs[-1].copy()
        last_log["tblr_coordinates"] = [last_log["tblr_coordinates"][-1]]
        last_log["occurrences_found"] = 1
        spatial_logs = [last_log]
        total_occurrences = 1
    elif position == "first" and spatial_logs:
        first_log = spatial_logs[0].copy()
        first_log["tblr_coordinates"] = [first_log["tblr_coordinates"][0]]
        first_log["occurrences_found"] = 1
        spatial_logs = [first_log]
        total_occurrences = 1

    return {"calculated_geometry": spatial_logs, "global_match_count": total_occurrences}

def conversational_synthesis_agent(state: AgenticSystemState):
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
    - If coordinates are present, format them cleanly using clean Markdown layout tables.
    - Always wrap structural file names like 'page (X).png' in clean bold markers.
    """
    context_payload = f"Input: {user_original_prompt} | Target: {resolved_query} | Type: {constraints.get('intent_type')} | Total: {total_matches} | Boxes: {json.dumps(geometry_facts)} | Tokens: {json.dumps(tokens)}"
    
    response = api_orchestrator.execute_with_retry(
        system_instruction=system_instruction, prompt_contents=context_payload, temp=1.0
    )
    final_report = {
        "chatbot_markdown_response": response.text,
        "telemetry": {"total_matches_found": total_matches, "tokens_consumed": tokens},
        "raw_geometry_manifest": geometry_facts
    }
    return {"final_execution_log": final_report}