# Document Spatial Intelligence System

This project is a comprehensive Document Spatial Intelligence system that combines a powerful multi-agent AI backend with a decoupled frontend application. The core system allows users to interact with and query spatial information extracted from documents, supporting both text-based conversational queries and multimodal image uploads. It efficiently catalogs books, pages, and bounding box coordinates for deep spatial search capabilities.

## System Architecture

The architecture consists of a robust backend API and a modern web frontend.

### Backend

The backend is a production-ready REST API built with **FastAPI** (`server.py`). It orchestrates a multi-agent workflow using **LangGraph** (`agents/graph.py`) to process user queries and retrieve spatial document data.

Key technologies used in the backend include:
- **FastAPI**: Serves the REST API endpoints and handles CORS.
- **LangGraph**: Manages the state and routing of the autonomous multi-agent pipeline.
- **Google Gemini API**: Powers the AI agents (using `gemini-2.5-flash`) for intent extraction, multimodal vision processing, and conversational synthesis. An `APIKeyRotator` ensures resilience and quota management.
- **EasyOCR**: The primary OCR engine for text extraction and precise spatial boundary detection.
- **SQLite**: A local database (`spatial_rag.db`) that acts as a spatial Retrieval-Augmented Generation (RAG) catalog, storing document metadata, full text, and spatial coordinate maps of text elements.

> [!NOTE]  
> **OCR Flexibility:** EasyOCR is used as the standard, robust OCR engine for extracting text natively in Python. If you prefer or require an alternative OCR engine (such as Tesseract), please check out the specific OCR branches (e.g., the `EasyOCR` branch is the current default).

#### Multi-Agent Pipeline

The core intelligence is driven by a configurable state engine graph with the following autonomous agents:
1. **Input Vision Agent**: A multimodal agent that uses Gemini's vision capabilities (or local OCR fallback) to extract target search phrases from uploaded image snapshots.
2. **Retrieval Agent (Intent Refiner)**: Analyzes conversational prompts to extract exact search constraints (like target word, intent type, occurrence limits) and performs fuzzy-matching against the local spatial database.
3. **Spatial Agent**: Computes pixel boundaries and bounding boxes for the requested terms across the indexed document spatial maps.
4. **Synthesis Agent**: The final "Spokesman" node that formats execution records, occurrence metrics, and layout geometry into natural, conversational Markdown responses.

#### API Endpoints

- `POST /api/chat`: Core endpoint for text-based conversational queries.
- `POST /api/upload`: Endpoint for multimodal image queries, where users can upload an image snippet to search.
- `GET /api/analytics`: Retrieves system database metrics (total pages cataloged, total documents indexed).
- `GET /api/view-page/{book_name}/{page_file_name}`: Static file stream handler to serve requested page layout canvas images.

### Frontend

The frontend is a modern web application built using **React** and **Vite** (located in the `frontend/` directory). It provides the user interface to interact with the backend API, displaying the chat, database analytics, and highlighted document canvasses.

## Directory Structure

```text
/
├── agents/               # LangGraph multi-agent pipeline definitions
│   ├── graph.py          # State graph workflow setup
│   ├── nodes.py          # Autonomous agent implementations
│   ├── pydantic_models.py# Data schemas for LLM intent extraction
│   └── state.py          # State schema definitions
├── config/               # Configuration and API key management
│   └── api_manager.py    # Rotates and manages Gemini API credentials
├── data/                 # Data ingestion scripts
│   ├── ingest_dataset.py # Script to OCR and load books into the DB
│   └── init_db.py        # Initializes SQLite schema
├── dataset/              # Dataset directory organized by books containing page images
│   ├── Book 1/           
│   │   ├── page (1).png  
│   │   └── page (2).png  
│   └── Book 2/           
├── frontend/             # React + Vite frontend application source code
├── tests/                # Test suites
├── tools/                # Helper tools
│   └── spatial_geometry.py # Functions for spatial math and coordinate matching
├── .env                  # Environment variables (e.g., GEMINI_API_KEY)
├── api_keys.json         # Array of API keys for the rotator
├── install.ps1           # PowerShell script to install dependencies
├── requirements.txt      # Python backend dependencies
├── run.ps1               # PowerShell script to start servers
├── server.py             # FastAPI backend server application
└── spatial_rag.db        # SQLite database containing indexed spatial data
```

## Setup and Installation

### Using PowerShell Scripts (Recommended for Windows)

We provide PowerShell scripts (`.ps1`) to easily install dependencies and run both servers simultaneously.

1. **Set Execution Policy**: Before running the scripts, you must allow script execution on your Windows machine. Open PowerShell as Administrator and run:
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
   *Type `Y` to confirm if prompted.*

2. **Install Tesseract OCR**:
   Download the Windows installer for Tesseract OCR from [UB-Mannheim's GitHub](https://github.com/UB-Mannheim/tesseract/wiki). Run the installer and ensure it installs to the `C:\Program Files\Tesseract-OCR` directory. Add this path to your system's Environment Variables (`PATH`).

3. **Configure API Keys**: Add your Gemini API keys.
   Create a `.env` file at the root:
   ```env
   GEMINI_API_KEY_1=your_api_key_here
   ```
   Or edit `api_keys.json` to include multiple keys for automatic rate-limit rotation.

4. **Install Dependencies**: Run the install script from the project root. This installs both Python and Node.js dependencies.
   ```powershell
   .\install.ps1
   ```

5. **Initialize Database and Ingest Data**:
   Ensure you have your images organized in the `dataset/` folder by book. Then run:
   ```bash
   python data/init_db.py
   python data/ingest_dataset.py
   ```

6. **Run the Application**:
   ```powershell
   .\run.ps1
   ```
   This script will launch the FastAPI backend in a new command window and start the Vite frontend development server in your current terminal.

### Manual Setup (For Linux / macOS / Advanced Users)

#### Backend Prerequisites

1. Ensure you have Python 3.7+ installed.
2. Install Tesseract OCR:
   - **Linux**: `sudo apt install tesseract-ocr`
   - **macOS**: `brew install tesseract`
   - **Windows**: Install the executable to the C drive and add it to your PATH.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Initialize the database and run data ingestion:
   ```bash
   python data/init_db.py
   python data/ingest_dataset.py
   ```
5. Start the FastAPI server:
   ```bash
   uvicorn server:app --host 127.0.0.1 --port 8000
   ```

#### Running the Frontend Manually

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
