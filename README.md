# Sustainable AI Assessment Platform

An end-to-end, **100% offline**, privacy-preserving assessment platform that automates the evaluation of handwritten examination answer sheets. Powered by a local multimodal Vision-Language Model (**Qwen-VL** via Ollama), FastAPI, React 19, and MongoDB.

---

## Key Highlights

- **100% Local & Privacy-Preserving**: Runs entirely on local hardware (CPU/GPU) with zero cloud dependencies and no external data transmission.
- **Unified Multimodal VLM Pipeline**: Replaces fragile multi-model chains (cloud OCR + regex + text SLM) with an end-to-end vision-language model (`qwen-eval`) performing handwriting transcription, LaTeX math parsing, diagram structural perception, and rubric alignment in a holistic pass.
- **Pre-Flight Health Check ("Are You Up?")**: Automatically pings the local model runner before kicking off batch processing to verify memory allocation in RAM (`llama-server.exe`), eliminating cold-start hangs and empty responses.
- **Real-Time Live SSE Stream Console**: Server-Sent Events (SSE) stream terminal-grade logs, model ping status, and stage progress directly into the frontend.
- **Human-in-the-Loop Triage (Stage 4)**: Automatically detects borderline scores (<60% or within 2.5% of grade boundaries) and handwriting ambiguities, routing them to educators for rapid review.
- **Detailed Run Logs**: Each pipeline execution generates a timestamped folder (`logs/{evaluation_id}/run_{timestamp}/`) containing full debug traces, token timings, and structured outputs.

---

## 5-Stage Offline Pipeline Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              5-STAGE OFFLINE VLM PIPELINE                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  [ Answer Sheet Image ] ──► [ Institutional Rubric (PDF/Text) ]                         │
│             │                               │                                          │
│             ▼                               ▼                                          │
│  ┌───────────────────────┐       ┌───────────────────────┐                             │
│  │ Stage 0: Preprocess   │       │ Pre-Flight Ping Check │ ──► "Are you up?" (0.5s)    │
│  │ Resize & 640px Norm   │       │ Model Loaded in RAM   │     (llama-server.exe)      │
│  └──────────┬────────────┘       └──────────┬────────────┘                             │
│             │                               │                                          │
│             └───────────────────────┬───────┘                                          │
│                                     ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Unified VLM Inference Pass (Local Qwen-VL)                                       │  │
│  │                                                                                  │  │
│  │  ► Stage 1: Unified Multimodal Transcription (Handwriting & LaTeX formulas)      │  │
│  │  ► Stage 2: Diagram & Structural Perception (Flowcharts, matrices, trees)        │  │
│  │  ► Stage 3: Dynamic Rubric Alignment & Scoring (Per-component rationale)         │  │
│  └──────────────────────────────────┬───────────────────────────────────────────────┘  │
│                                     │                                                  │
│                                     ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Stage 4: Flagging & Educator Triage Queue                                        │  │
│  │  ► Auto-detects borderline scores & ambiguous handwriting                         │  │
│  │  ► Routes flagged scripts for educator approval in Review Queue                  │  │
│  └──────────────────────────────────┬───────────────────────────────────────────────┘  │
│                                     │                                                  │
│                                     ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Persistence & Real-Time Observability                                             │  │
│  │  ► MongoDB: Sheet scores, component breakdown, transcriptions, student metadata  │  │
│  │  ► Live SSE Stream: /api/evaluations/{id}/pipeline/stream                        │  │
│  │  ► Dedicated Run Logs: logs/{evaluation_id}/{run_id}/run.log                      │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend
- **FastAPI** — High-performance asynchronous REST API framework
- **Uvicorn** — ASGI web server
- **Motor / MongoDB** — Asynchronous document store for evaluations, answer sheets, rubrics, and scores
- **Ollama (`llama-server.exe`)** — Local GGUF inference runner for the `qwen-eval` multimodal vision model
- **Pillow** — Image normalization and bilinear downsampling
- **Server-Sent Events (SSE)** — Real-time event bus broadcasting execution progress to clients
- **ReportLab** — PDF report generator

### Frontend
- **React 19 & TypeScript** — Modern type-safe single-page application
- **Vite 7** — Fast HMR build tool and dev server
- **Tailwind CSS 4** — Utility-first responsive styling
- **React Router 7** — Client-side navigation supporting both `/evaluation/:id` and `/evaluations/:id` aliases
- **Custom SSE Live Terminal** — Real-time execution log viewer with auto-scroll and one-click copy

---

## Project Structure

```
capstone/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application entrypoint & lifespan
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic settings & model configuration
│   │   │   ├── mongodb.py              # Motor async database connection
│   │   │   ├── event_bus.py            # SSE in-memory event bus
│   │   │   ├── logging_config.py       # Dedicated run log folder handlers
│   │   │   └── arq_pool.py             # Redis / Arq pool manager
│   │   ├── services/
│   │   │   ├── unified_vlm_service.py  # Local Qwen-VL multimodal perception & evaluation
│   │   │   ├── rubric_parser.py        # Institutional rubric parser (PDF/TXT)
│   │   │   └── ocr_service.py          # OCR service adapter
│   │   ├── routers/
│   │   │   ├── evaluations.py          # Evaluation CRUD operations
│   │   │   ├── sheets.py               # Sheet upload, listing, and deletion
│   │   │   ├── pipeline.py             # 5-Stage pipeline start, SSE stream & status
│   │   │   ├── results.py              # Results summary, score breakdown & triage
│   │   │   └── export.py               # CSV, PDF, and TXT report generation
│   │   └── worker.py                   # In-process background sheet extraction worker
│   ├── logs/                           # Per-evaluation execution run logs
│   ├── uploads/                        # Uploaded answer sheet images & rubrics
│   └── requirements.txt                # Python backend dependencies
│
└── frontend/
    ├── src/
    │   ├── App.tsx                     # Route definitions & layout wrapping
    │   ├── pages/
    │   │   ├── Home.tsx                # Evaluation list & status dashboard
    │   │   ├── CreateEvaluation.tsx    # Evaluation setup wizard
    │   │   ├── UploadSheets.tsx        # Answer sheet & rubric upload
    │   │   ├── ProcessEvaluation.tsx   # 5-Stage progress tracker & SSE live console
    │   │   ├── ResultsOverview.tsx     # Score distribution & Stage 4 triage filters
    │   │   ├── ScriptDetails.tsx       # Per-student question breakdown & verification
    │   │   └── ExportResults.tsx       # Export controls (CSV / PDF / TXT)
    │   ├── components/                 # Layout, Sidebar, Navbar, and UI widgets
    │   └── api/                        # Centralized fetch client & API endpoints
    └── package.json                    # Frontend dependencies
```

---

## Quick Start Guide

### Prerequisites
1. **Python 3.10+**
2. **Node.js 18+** & npm
3. **MongoDB** (running locally on `mongodb://localhost:27017`)
4. **Ollama** installed on your system (`http://localhost:11434`)

### 1. Configure the Local VLM Model in Ollama

Create a dedicated direct-response model profile (`qwen-eval`) in Ollama to ensure deterministic JSON evaluation without chain-of-thought token stalls:

```bash
# In Ollama CLI, create the optimized model
ollama create qwen-eval -f ./Modelfile
```

Ensure the model responds:
```bash
ollama run qwen-eval "Respond with 1 word: ready"
```

### 2. Backend Setup

```bash
cd capstone/backend

# Create and activate virtual environment
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server with reload
python -m uvicorn app.main:app --reload --port 8000
```

The backend starts at `http://localhost:8000`. Interactive OpenAPI documentation is accessible at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 3. Frontend Setup

```bash
cd capstone/frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

The frontend application starts at `http://localhost:5173`.

---

## Workflow Walkthrough

1. **Create Evaluation**: Go to `http://localhost:5173`, click **New Evaluation**, specify course subject, maximum marks, and evaluation name.
2. **Upload Rubric & Sheets**: Upload your institutional marking rubric (PDF or text) and student answer sheets (JPG/PNG).
3. **Run Pipeline**:
   - Click **Start Pipeline**.
   - The backend performs an automated **pre-flight ping** (`"Are you up?"`), warming `llama-server.exe` in RAM (~6.87 GB).
   - Watch real-time logs stream in the **SSE Terminal** as each sheet undergoes image normalization, handwriting OCR, LaTeX extraction, diagram parsing, and rubric grading.
4. **Inspect Results & Triage**:
   - Navigate to the **Results Overview** (`/evaluation/:id/results`).
   - Scripts needing educator review (Stage 4 triage) are flagged with specific review rationales.
   - Click any script to inspect component-by-component scoring, model feedback, and transcribed answers.
5. **Export Reports**: Generate comprehensive CSV, PDF, or TXT evaluation reports ready for academic records.

---

## API Endpoints Summary

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/api/evaluations` | Create a new evaluation |
| `GET`  | `/api/evaluations` | List all evaluations |
| `GET`  | `/api/evaluations/{id}` | Get evaluation details |
| `DELETE` | `/api/evaluations/{id}` | Delete an evaluation & related records |
| `POST` | `/api/evaluations/{id}/sheets` | Upload student answer sheets |
| `GET`  | `/api/evaluations/{id}/sheets` | List sheets with processing statuses |
| `POST` | `/api/evaluations/{id}/rubric` | Upload institutional grading rubric |
| `POST` | `/api/evaluations/{id}/pipeline/start` | Trigger 5-stage offline evaluation pipeline |
| `GET`  | `/api/evaluations/{id}/pipeline/status` | Poll pipeline execution progress |
| `GET`  | `/api/evaluations/{id}/pipeline/stream` | Real-time SSE stream of run logs and stage events |
| `GET`  | `/api/evaluations/{id}/results` | Aggregated class performance & triage summary |
| `GET`  | `/api/evaluations/{id}/results/{sheet_id}` | Detailed student question-by-question scoring |
| `POST` | `/api/evaluations/{id}/review_queue/{sheet_id}/resolve` | Resolve/approve flagged script score |
| `GET`  | `/api/evaluations/{id}/export/{format}` | Export results as `csv`, `pdf`, or `txt` |

---

## License

This project is developed for institutional academic assessment automation. All model execution remains on-device with zero telemetry.
