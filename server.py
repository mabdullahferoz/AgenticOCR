import os
import json
import sqlite3
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

# Import your pristine compiled multi-agent graph workflow system
from agents.graph import agent_system

app = FastAPI(
    title="Document Spatial Intelligence Multi-Agent API",
    description="Comprehensive production REST backend orchestrating LangGraph workflows, dataset streaming, and vision processing."
)

# Configure CORS so your decoupled React application can call this API safely from any port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compute path to root DB file relative to this folder position
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "spatial_rag.db")
DATASET_IMAGES_DIR = os.path.join(BASE_DIR, "dataset", "images")

class ChatPayload(BaseModel):
    message: str
    awaiting_confirmation: bool = False
    suggested_correction: Optional[str] = None

# =======================================================
# ENDPOINT 1: CORE CONVERSATIONAL AGENT ROUTE
# =======================================================
@app.post("/api/chat")
async def process_agent_query(payload: ChatPayload):
    try:
        # Rehydrate the exact LangGraph shared blackboard state from the incoming React request payload
        current_state = {
            "user_input": payload.message,
            "resolved_query": "",
            "query_constraints": {},
            "database_raw_hits": [],
            "calculated_geometry": [],
            "global_match_count": 0,
            "final_execution_log": {},
            "awaiting_confirmation": payload.awaiting_confirmation,
            "suggested_correction": payload.suggested_correction
        }
        
        # Invoke the multi-agent graph network worker pipeline
        updated_state = agent_system.invoke(current_state)
        
        # Isolate the structured report response built by the Synthesis Agent node
        execution_log = updated_state.get("final_execution_log", {})
        
        return {
            "chatbot_response": execution_log.get("chatbot_markdown_response", "No response text compiled."),
            "awaiting_confirmation": updated_state.get("awaiting_confirmation", False),
            "suggested_correction": updated_state.get("suggested_correction"),
            "telemetry": {
                "total_tokens": updated_state.get("token_usage", {}).get("total_tokens", 0),
                "global_hits": updated_state.get("global_match_count", 0)
            },
            "raw_graph_state": {k: v for k, v in updated_state.items() if k != "database_raw_hits"}
        }
        
    except Exception as e:
        print(f"[ERROR] Core Multi-Agent Pipeline Crash: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Graph Runtime Error: {str(e)}")


# =======================================================
# ENDPOINT 2: MULTIMODAL SNAPSHOT IMAGE UPLOAD ROUTE
# =======================================================
@app.post("/api/upload")
async def handle_multimodal_image_query(file: UploadFile = File(...)):
    try:
        # 1. Setup a clean local query image file caching directory
        temp_dir = os.path.join(BASE_DIR, "temp_queries")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Save incoming file payload buffer onto local workspace disk safely
        file_path = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        print(f"[Server API]: Staged query image file snippet at: {file_path}")
        
        # 2. Build our standard pipeline rehydration map starting directly at the InputVisionAgent node
        initial_vision_state = {
            "user_input": file_path, # Path string automatically routes graph down 'vision_path'
            "resolved_query": "",
            "query_constraints": {},
            "database_raw_hits": [],
            "calculated_geometry": [],
            "global_match_count": 0,
            "final_execution_log": {},
            "awaiting_confirmation": False,
            "suggested_correction": None
        }
        
        # 3. Fire the full engine execution sequence
        updated_state = agent_system.invoke(initial_vision_state)
        execution_log = updated_state.get("final_execution_log", {})
        
        return {
            "chatbot_response": execution_log.get("chatbot_markdown_response", "No response compiled."),
            "resolved_query": updated_state.get("resolved_query", ""),
            "awaiting_confirmation": updated_state.get("awaiting_confirmation", False),
            "suggested_correction": updated_state.get("suggested_correction"),
            "telemetry": {
                "total_tokens": updated_state.get("token_usage", {}).get("total_tokens", 0),
                "global_hits": updated_state.get("global_match_count", 0)
            },
            "raw_graph_state": {k: v for k, v in updated_state.items() if k != "database_raw_hits"}
        }
        
    except Exception as e:
        print(f"[ERROR] Multimodal Ingestion Endpoint Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Vision Processing Error: {str(e)}")


# =======================================================
# ENDPOINT 3: GLOBAL OVERVIEW BACKEND METRICS
# =======================================================
@app.get("/api/analytics")
async def get_system_database_metrics():
    """Fetches high-level metrics directly from the database for your React dashboard overview header cards."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database catalog file missing from root system.")
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Compute total unique pages indexed
        cursor.execute("SELECT COUNT(*) FROM document_pages")
        total_pages = cursor.fetchone()[0]
        
        # Compute total parent document container bounds
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]
        
        conn.close()
        return {
            "total_documents_indexed": total_docs,
            "total_pages_cataloged": total_pages,
            "system_status": "Healthy & Operational"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Diagnostic Reading Failure: {str(e)}")


# =======================================================
# ENDPOINT 4: STATIC FILE STREAM HANDLER (PAGE STREAMER)
# =======================================================
@app.get("/api/view-page/{filename}")
async def fetch_document_canvas_image(filename: str):
    """Streams a requested page layout canvas image straight to React to render custom polygon box highlights."""
    clean_filename = os.path.basename(filename) # Path traversal sanitization sweep
    target_image_path = os.path.join(DATASET_IMAGES_DIR, clean_filename)
    
    if not os.path.exists(target_image_path):
        raise HTTPException(status_code=404, detail=f"Requested page layout canvas item '{clean_filename}' not found.")
        
    return FileResponse(target_image_path)


if __name__ == "__main__":
    import uvicorn
    # Launches the fully operational, multi-endpoint system server on port 8000
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)