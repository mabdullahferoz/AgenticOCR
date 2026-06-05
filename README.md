# Document Spatial Intelligence System

This project is a comprehensive Document Spatial Intelligence system that combines a powerful multi-agent AI backend with a decoupled frontend application. The core system allows users to interact with and query spatial information extracted from documents, supporting both text-based conversational queries and multimodal image uploads.

## System Architecture

The architecture consists of a robust backend API and a modern web frontend.

### Backend

The backend is a production-ready REST API built with **FastAPI** (`server.py`). It orchestrates a multi-agent workflow using **LangGraph** (`agents.py`) to process user queries and retrieve spatial document data.

Key technologies used in the backend include:
- **FastAPI**: Serves the REST API endpoints and handles CORS.
- **LangGraph**: Manages the state and routing of the autonomous multi-agent pipeline.
- **Google Gemini API**: Powers the AI agents (using `gemini-2.5-flash`) for intent extraction, multimodal vision processing, and conversational synthesis. An `APIKeyRotator` ensures resilience and quota management.
- **Tesseract OCR**: Acts as a fallback for extracting text from uploaded query images.
- **SQLite**: A local database (`spatial_rag.db`) that acts as a spatial Retrieval-Augmented Generation (RAG) catalog, storing document metadata, full text, and spatial coordinate maps of text elements.

#### Multi-Agent Pipeline

The core intelligence is driven by a configurable state engine graph with the following autonomous agents:
1. **Input Vision Agent**: A multimodal agent that uses Gemini's vision capabilities (or Tesseract OCR) to extract target search phrases from uploaded image snapshots.
2. **Retrieval Agent (Intent Refiner)**: Analyzes conversational prompts to extract exact search constraints (like target word, intent type, occurrence limits) and performs fuzzy-matching against the local spatial database.
3. **Spatial Agent**: Computes pixel boundaries and bounding boxes for the requested terms across the indexed document spatial maps.
4. **Synthesis Agent**: The final "Spokesman" node that formats execution records, occurrence metrics, and layout geometry into natural, conversational Markdown responses.

#### API Endpoints

- `POST /api/chat`: Core endpoint for text-based conversational queries.
- `POST /api/upload`: Endpoint for multimodal image queries, where users can upload an image snippet to search.
- `GET /api/analytics`: Retrieves system database metrics (total pages cataloged, total documents indexed).
- `GET /api/view-page/{filename}`: Static file stream handler to serve requested page layout canvas images.

### Frontend

The frontend is a modern web application built using **React** and **Vite** (located in the `frontend/` directory). It provides the user interface to interact with the backend API, displaying the chat, database analytics, and highlighted document canvasses.

## Directory Structure

```text
/
├── agents.py             # LangGraph multi-agent pipeline definitions
├── server.py             # FastAPI backend server
├── spatial_rag.db        # SQLite database containing indexed spatial data
├── requirements.txt      # Python backend dependencies
├── .env                  # Environment variables (e.g., GEMINI_API_KEY)
├── tools/                # Helper tools
│   └── spatial_geometry.py # Functions for spatial math and coordinate matching
├── dataset/
│   └── images/           # Directory serving static document canvas images
├── temp_queries/         # Temporary directory for uploaded query image processing
└── frontend/             # React + Vite frontend application source code
```

## Setup and Installation

### Backend Prerequisites

1. Ensure you have Python installed.
2. Install the Tesseract OCR engine on your system.
3. Configure your API keys in a `.env` file at the root of the project:
   ```env
   GEMINI_API_KEY_1=your_api_key_here
   # You can add multiple keys for automatic rotation:
   # GEMINI_API_KEY_2=...
   ```

### Running the Backend

1. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the FastAPI server using Uvicorn:
   ```bash
   uvicorn server:app --host 127.0.0.1 --port 8000 --reload
   ```
   Or simply run the `server.py` script:
   ```bash
   python server.py
   ```

### Running the Frontend

Navigate to the `frontend/` directory and use npm to run the development server:

```bash
cd frontend
npm install
npm run dev
```

## Features

- **Conversational Queries**: Ask natural language questions like "find the last instance of the word 'TOTAL'".
- **Spatial Bounding Boxes**: The system returns exact bounding box coordinates for the text found in the documents.
- **Multimodal Support**: Upload a cropped image of text, and the system will find its occurrences across the cataloged documents.
- **Resilient API Handling**: Automatic rotation of Gemini API keys when quota limits are reached.
- **Fuzzy Search Correction**: If an exact term isn't found, the system intelligently suggests the closest match from the database vocabulary and awaits user confirmation.
