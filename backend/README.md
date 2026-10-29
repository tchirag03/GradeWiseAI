# Sustainable AI Assessment Platform — Backend

Asynchronous FastAPI backend providing offline multimodal assessment, real-time SSE streaming, and persistent MongoDB storage.

---

## Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │          FastAPI Routers               │
                      │  evaluations │ sheets │ pipeline │ ... │
                      └──────────────────┬─────────────────────┘
                                         │
                 ┌───────────────────────┼────────────────────────┐
                 ▼                       ▼                        ▼
       ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
       │ Unified VLM Svc  │    │  SSE Event Bus   │    │ Logging & Run Dirs  │
       │ (Local Qwen-VL)  │    │  (Live Stream)   │    │ (Dedicated Folders) │
       └─────────┬────────┘    └──────────────────┘    └─────────────────────┘
                 │
                 ▼
       ┌──────────────────┐
       │   Ollama Local   │ ◄── Pre-Flight Ping ("Are you up?")
       │ (llama-server)   │ ◄── Multimodal Perception & Rubric Grading Pass
       └──────────────────┘
```

### Key Modules

- **`app/services/unified_vlm_service.py`**:
  - Encapsulates interaction with local Ollama (`qwen-eval`).
  - Pre-flight model check (`ping_model`): sends a minimal 5-token ping to ensure `llama-server.exe` is allocated in memory before heavy tasks run.
  - Image normalization: compresses and bilinearly downsamples high-res sheet scans to 640px to maximize vision throughput while maintaining handwriting clarity.
  - Holistic grading: extracts text, LaTeX equations, topological diagram descriptions, and evaluates against rubric mark bands.
  - Zero hardcoded fallbacks or mock data.
- **`app/routers/pipeline.py`**:
  - `POST /api/evaluations/{id}/pipeline/start`: Pre-checks model availability, initializes timestamped run directories (`logs/{eval_id}/run_{ts}/`), and dispatches in-process sequential evaluation.
  - `GET /api/evaluations/{id}/pipeline/stream`: Asynchronous Server-Sent Events (SSE) generator streaming run events (`vlm_ping`, `vlm_dispatch`, `sheet_completed`, etc.) directly to the client.
- **`app/worker.py`**:
  - In-process background job runner driving each sheet through the 5-stage offline pipeline without external worker process overhead.
- **`app/core/logging_config.py`**:
  - Creates dedicated run folders for each execution (`logs/{eval_id}/{run_id}/run.log`) capturing token counts, prompt evaluation times, and raw JSON outputs.

---

## Configuration (`app/core/config.py` / `.env`)

Key configuration options configurable via environment variables or `.env`:

| Variable | Default | Purpose |
|:---------|:--------|:--------|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection URI |
| `DB_NAME` | `evaluation_db` | Main database name |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Local Ollama API server |
| `OLLAMA_MODEL` | `qwen-eval` | Model name to use for multimodal evaluation |
| `REDIS_HOST` | `localhost` | Redis server hostname (optional) |
| `REDIS_PORT` | `6379` | Redis server port (optional) |

---

## Local Development & Setup

### 1. Requirements
- Python 3.10+
- Local MongoDB running on `mongodb://localhost:27017`
- Local Ollama running on `http://127.0.0.1:11434` with model `qwen-eval`

### 2. Setup Virtual Environment

```bash
# Navigate to backend directory
cd capstone/backend

# Create virtual environment
python -m venv .venv

# Activate on Windows:
.venv\Scripts\Activate.ps1
# Activate on Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Backend Server

```bash
python -m uvicorn app.main:app --reload --port 8000
```

The server will be available at `http://127.0.0.1:8000`.

- **Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`

---

## Testing & Verification Scripts

Standalone utility scripts are available for debugging and testing:

```bash
# Run pre-flight ping test to verify model runner is active in RAM
python -c "import asyncio, sys; sys.path.insert(0, '.'); from app.services.unified_vlm_service import get_unified_vlm_service; print(asyncio.run(get_unified_vlm_service().ping_model()))"
```

---

## Directory Layout

```
backend/
├── app/
│   ├── main.py                  # Lifespan startup, database initialization & CORS
│   ├── worker.py                # In-process sheet extraction and evaluation worker
│   ├── core/                    # Config, Mongo, event bus, logging
│   ├── routers/                 # Endpoint routers (evaluations, sheets, pipeline, results, export)
│   ├── schemas/                 # Pydantic request/response schemas
│   └── services/                # Unified VLM service, rubric parser, OCR adapter
├── logs/                        # Generated execution run folders (run.log, summary.json)
├── uploads/                     # Answer sheet files and rubric uploads
└── requirements.txt             # Project requirements
```
