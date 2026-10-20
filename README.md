# Sustainable AI Assessment Platform

An end-to-end, AI-powered evaluation system that automates the grading of handwritten answer sheets using a three-stage pipeline: **OCR → Text Structuring → SLM Evaluation**. Built as a full-stack application with a FastAPI backend and React frontend.

---

## Table of Contents

- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Three-Stage AI Pipeline](#three-stage-ai-pipeline)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Backend Architecture](#backend-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Database Design](#database-design)
- [API Reference](#api-reference)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)

---

## Project Overview

The platform addresses the challenge of **manually grading large volumes of handwritten answer sheets** in educational institutions. Instead of requiring human evaluators to read and score each paper individually, the system:

1. **Scans** handwritten answer sheets (uploaded as images)
2. **Extracts** text from the images using OCR
3. **Structures** the raw text into question-answer pairs
4. **Evaluates** answers against a rubric using a Small Language Model (SLM)
5. **Generates** detailed results, analytics, and exportable reports

All AI inference runs **locally on-device** — no cloud APIs, no data leaves the machine.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │
│  │   Home   │ │  Upload  │ │ Process  │ │ Results  │ │ Export  │  │
│  │   Page   │ │  Sheets  │ │ Pipeline │ │ Overview │ │ Reports │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘  │
│       └────────────┴────────────┴────────────┴────────────┘        │
│                          Axios HTTP Client                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST API (JSON)
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI + Uvicorn)                     │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                        API Layer (Routers)                      │  │
│  │  evaluations │ sheets │ ocr │ structuring │ slm │ results │ …  │  │
│  └──────────────────────────┬──────────────────────────────────────┘  │
│                             │                                        │
│  ┌──────────────────────────▼──────────────────────────────────────┐  │
│  │                     Service Layer (AI Models)                   │  │
│  │  ┌──────────────┐  ┌───────────────────┐  ┌─────────────────┐  │  │
│  │  │  OCR Service  │  │ Structuring Svc   │  │   SLM Service   │  │  │
│  │  │ (Mistral OCR) │  │ (Regex+Heuristic) │  │  (Qwen2.5-0.5B) │  │  │
│  │  └──────────────┘  └───────────────────┘  └─────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                             │                                        │
│  ┌──────────────────────────▼──────────────────────────────────────┐  │
│  │                      Data Layer                                 │  │
│  │  ┌─────────────────┐  ┌─────────────┐  ┌────────────────────┐  │  │
│  │  │   MongoDB        │  │   Redis      │  │  File Storage      │  │  │
│  │  │   (Documents)    │  │   (Cache +   │  │  (Uploaded Images) │  │  │
│  │  │                  │  │    Job Queue) │  │                    │  │  │
│  │  └─────────────────┘  └─────────────┘  └────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Three-Stage AI Pipeline

Each stage runs as an **asynchronous background job** with progress tracking and status polling.

### Stage 1: OCR — Handwritten Text Extraction

| Attribute      | Detail |
|:---------------|:-------|
| **Service**    | Mistral OCR API (`mistral-ocr-latest`) |
| **Input**      | Uploaded answer sheet image (PNG/JPG) |
| **Output**     | Markdown-formatted extracted text |
| **Runs on**    | Cloud (Mistral AI Platform) |

**How it works:**
1. Image is read and base64-encoded
2. Sent to Mistral's `ocr.process()` with `mistral-ocr-latest` model
3. Markdown text is extracted from all response pages
4. Extracted text and processing time are stored on the sheet document in MongoDB

### Stage 2: Text Structuring — Q&A Parsing

| Attribute      | Detail |
|:---------------|:-------|
| **Method**     | Regex + Heuristic rules (no ML model needed) |
| **Input**      | Raw OCR text |
| **Output**     | Structured question-answer objects |

**How it works:**
1. Regex patterns detect question markers (`Q1`, `1.`, `Question 1`, etc.)
2. Text is split into individual question blocks
3. Each question is parsed for:
   - **Answer steps** (Step 1, a), i., etc.)
   - **Code blocks** (detected via language-specific indicators)
   - **Keywords** (matched against a CS/programming keyword dictionary)
   - **Complexity** (Big-O notation extraction)
4. Structured data is stored as a nested document on the sheet

### Stage 3: SLM Evaluation — AI Grading

| Attribute      | Detail |
|:---------------|:-------|
| **Model**      | `Qwen/Qwen2.5-0.5B-Instruct` (Small Language Model) |
| **Quantization** | None (float32 for smooth CPU execution) |
| **Input**      | Structured Q&A + rubric components |
| **Output**     | Per-question scores, component breakdown, letter grade |

**How it works:**
1. For each question, a grading prompt is constructed with:
   - The question text
   - The student's answer
   - Rubric components with mark allocations
2. The SLM generates a JSON response with per-component scores and feedback
3. Response is parsed (with fallback heuristics if JSON is malformed)
4. Total score, percentage, and letter grade are calculated
5. Full evaluation result is persisted to MongoDB

**Grading Scale:**

| Percentage | Grade |
|:-----------|:------|
| ≥ 90%      | A+    |
| ≥ 80%      | A     |
| ≥ 70%      | B+    |
| ≥ 60%      | B     |
| ≥ 50%      | C     |
| ≥ 40%      | D     |
| < 40%      | F     |

---

## Tech Stack

### Backend

| Technology | Purpose |
|:-----------|:--------|
| **FastAPI** | Async web framework with automatic OpenAPI docs |
| **Uvicorn** | ASGI server |
| **Pydantic** | Request/response validation and serialization |
| **MongoDB** (Motor) | Document database for evaluations, sheets, results |
| **Redis** | Caching layer and background job queue |
| **Mistral OCR** | Cloud OCR API for handwritten text extraction |
| **PyTorch** | Deep learning runtime for SLM |
| **Transformers** (HuggingFace) | Model loading and inference pipeline (SLM) |
| **Pillow** | Image preprocessing |
| **ReportLab** | PDF report generation |

### Frontend

| Technology | Purpose |
|:-----------|:--------|
| **React 19** | UI component framework |
| **TypeScript** | Type-safe application logic |
| **Vite 7** | Build tool and dev server |
| **Tailwind CSS 4** | Utility-first styling |
| **React Router 7** | Client-side routing |
| **Axios** | HTTP client for API communication |
| **Lucide React** | Icon library |
| **Redux Toolkit** | State management |

---

## Project Structure

```
pp1/
├── README.md                      ← You are here
│
├── backend/
│   ├── .env                       # Environment variables
│   ├── requirements.txt           # Python dependencies
│   ├── app/
│   │   ├── main.py                # FastAPI app + lifespan (model init)
│   │   │
│   │   ├── core/                  # Infrastructure
│   │   │   ├── config.py          # Pydantic settings (env-driven)
│   │   │   ├── mongodb.py         # Motor async MongoDB connection
│   │   │   └── redis_client.py    # Redis async connection
│   │   │
│   │   ├── services/              # AI Model Services (singletons)
│   │   │   ├── ocr_service.py     # TrOCR handwritten text extraction
│   │   │   ├── structuring_service.py  # Regex Q&A parser
│   │   │   └── slm_service.py     # Qwen2.5-0.5B answer evaluation
│   │   │
│   │   ├── schemas/               # Pydantic Models (API contracts)
│   │   │   ├── common.py          # Shared types (SuccessResponse, etc.)
│   │   │   ├── evaluation.py      # Evaluation CRUD schemas
│   │   │   ├── sheet.py           # Sheet upload schemas
│   │   │   ├── structuring.py     # Structured Q&A schemas
│   │   │   ├── slm.py             # SLM evaluation result schemas
│   │   │   ├── rubric.py          # Rubric component schemas
│   │   │   ├── script.py          # Answer script schemas
│   │   │   ├── student.py         # Student schemas
│   │   │   ├── analytics.py       # Analytics schemas
│   │   │   ├── queue.py           # Job queue schemas
│   │   │   └── settings.py        # App settings schemas
│   │   │
│   │   ├── routers/               # API Endpoints
│   │   │   ├── evaluations.py     # CRUD: create, list, get, delete
│   │   │   ├── sheets.py          # Upload, list, delete sheets
│   │   │   ├── ocr.py             # Start OCR, poll status, get result
│   │   │   ├── structuring.py     # Start structuring, poll, get result
│   │   │   ├── slm.py             # Start SLM eval, poll, get result
│   │   │   ├── results.py         # Aggregated results + detailed view
│   │   │   ├── export.py          # CSV and PDF export
│   │   │   ├── settings.py        # App settings management
│   │   │   ├── scripts.py         # Answer script management
│   │   │   ├── evaluation_jobs.py # Job history
│   │   │   ├── analytics.py       # Analytics endpoints
│   │   │   └── performance.py     # Performance metrics
│   │   │
│   │   └── db/                    # Database Layer
│   │       ├── repositories/      # CRUD operations
│   │       │   ├── rubric_repo.py
│   │       │   ├── script_repo.py
│   │       │   └── student_repo.py
│   │       ├── queries/           # Aggregation pipelines + indexes
│   │       │   ├── aggregation_queries.py
│   │       │   └── index_setup.py
│   │       └── services/          # Redis-backed services
│   │           ├── cache_service.py
│   │           ├── queue_service.py
│   │           └── status_service.py
│   │
│   └── scripts/                   # Utility scripts
│       ├── seed_data.py           # MongoDB seed data
│       └── benchmark.py           # Performance benchmarks
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx               # App entry point
        ├── App.tsx                # Route definitions
        ├── index.css              # Global styles
        │
        ├── pages/                 # Page Components
        │   ├── Home.tsx           # Dashboard with evaluation list
        │   ├── CreateEvaluation.tsx  # New evaluation form
        │   ├── UploadSheets.tsx   # Drag-and-drop sheet upload
        │   ├── ProcessEvaluation.tsx # Pipeline progress tracker
        │   ├── ResultsOverview.tsx   # Score summary + charts
        │   ├── ScriptDetails.tsx  # Per-student detailed breakdown
        │   ├── ExportResults.tsx  # CSV/PDF export controls
        │   ├── Settings.tsx       # App configuration
        │   ├── RubricBuilder.tsx  # Custom rubric creation
        │   ├── OpenEvaluation.tsx # Open existing evaluation
        │   └── NotFound.tsx       # 404 page
        │
        ├── components/            # Reusable Components
        │   ├── Layout.tsx         # App shell with Navbar
        │   ├── EvaluationLayout.tsx # Evaluation-scoped wrapper
        │   ├── Navbar.tsx         # Top navigation bar
        │   ├── Sidebar.tsx        # Evaluation step sidebar
        │   ├── Footer.tsx         # Page footer
        │   ├── Button.tsx
        │   ├── Card.tsx
        │   ├── Modal.tsx
        │   └── ProgressBar.tsx
        │
        ├── api/                   # API Client Layer
        │   ├── index.ts           # Axios instance + interceptors
        │   ├── endpoints.ts       # All endpoint URL constants
        │   ├── common.ts          # Shared types
        │   ├── evaluations.ts     # Evaluation API calls
        │   ├── evaluation.ts      # Single evaluation calls
        │   ├── sheets.ts          # Sheet upload API
        │   ├── ocr.ts             # OCR pipeline API
        │   ├── structuring.ts     # Structuring pipeline API
        │   ├── results.ts         # Results API
        │   ├── export.ts          # Export API
        │   └── settings.ts        # Settings API
        │
        └── types/                 # TypeScript type definitions
```

---

## Backend Architecture

### Layered Design

The backend follows a **three-layer architecture**:

```
              ┌──────────────────────────────┐
              │     Routers (API Layer)       │  ← HTTP request/response
              │  Validates input, returns JSON │
              └──────────────┬───────────────┘
                             │
              ┌──────────────▼───────────────┐
              │    Services (Business Logic)   │  ← AI model inference
              │  Singletons loaded at startup  │
              └──────────────┬───────────────┘
                             │
              ┌──────────────▼───────────────┐
              │   Data Layer (Repositories)    │  ← MongoDB, Redis, Files
              │  CRUD, aggregation, caching    │
              └──────────────────────────────┘
```

### Application Lifecycle

```python
# Startup sequence (main.py lifespan):
1. connect_db()              # MongoDB connection via Motor
2. connect_redis()           # Redis connection
3. ensure_indexes()          # Create MongoDB indexes
4. init_ocr_service()        # Mistral OCR client
5. init_structuring_service() # Initialize regex parser
6. init_slm_service()        # Load Qwen2.5-0.5B (~1GB)
7. start_worker()            # Redis job queue consumer
```

The Mistral OCR client and the SLM model are initialised **once at startup** and reused across all requests via the singleton pattern.

### Background Job Pattern

All three pipeline stages follow the same asynchronous pattern:

```
POST /start  →  Creates job record  →  Returns job_id immediately
                     │
                     ▼
            asyncio.create_task()  →  Background worker processes sheets
                     │
                     ▼
            Worker updates progress in MongoDB after each sheet
                     │
GET /status  →  Reads job record  →  Returns {completed, failed, percentage}
                     │
GET /result  →  Reads sheet doc   →  Returns per-sheet result
```

This ensures the API never blocks on long-running AI inference.

---

## Frontend Architecture

### Routing Structure

```
/                                    → Home (dashboard)
/evaluation/new                      → Create new evaluation
/evaluation/:id/open                 → Open existing evaluation
/evaluation/:id/upload               → Upload answer sheets
/evaluation/:id/rubric               → Build grading rubric
/evaluation/:id/process              → Run AI pipeline (OCR → Structure → Evaluate)
/evaluation/:id/results              → View results summary
/evaluation/:id/results/:scriptId    → View detailed per-student breakdown
/evaluation/:id/export               → Export CSV/PDF
/settings                            → App settings
```

### Data Flow

```
User Action → Page Component → API Client (Axios) → Backend Router
                                                          │
                                                     (processes)
                                                          │
                                          ← JSON Response ←
```

---

## Database Design

### MongoDB Collections

| Collection | Purpose | Key Fields |
|:-----------|:--------|:-----------|
| `evaluations` | Top-level evaluation entity | `name`, `subject`, `max_marks`, `answer_type`, `status` |
| `sheets` | Individual answer sheets | `evaluation_id`, `file_path`, `status`, `ocr_text`, `structured_data`, `evaluation_result` |
| `rubrics` | Grading rubric definitions | `components: [{name, marks}]` |
| `scripts` | Answer script records | `student_id`, `question_id`, `text`, `evaluation` |
| `students` | Student information | `name`, `roll_no` |
| `ocr_jobs` | OCR job tracking | `evaluation_id`, `total`, `completed`, `failed`, `status` |
| `structuring_jobs` | Structuring job tracking | Same structure as ocr_jobs |
| `slm_jobs` | SLM evaluation job tracking | Same structure as ocr_jobs |

### Sheet Status Lifecycle

```
uploaded
   │
   ▼
ocr-pending → ocr-processing → ocr-completed
                                     │
                                     ▼
              structuring-pending → structuring-processing → structuring-completed
                                                                   │
                                                                   ▼
                                    evaluation-pending → evaluation-processing → evaluation-completed
```

Each `*-failed` status allows the stage to be retried.

### Redis Usage

- **Caching**: Stores frequently accessed query results with TTL-based expiry
- **Job Queue**: Lightweight background task queue for batch operations
- **Status Tracking**: Real-time pipeline stage status updates

---

## API Reference

Base URL: `http://localhost:8000/api`

### Evaluation Management
| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/evaluations` | Create a new evaluation |
| `GET` | `/evaluations` | List all evaluations |
| `GET` | `/evaluations/{id}` | Get evaluation details |
| `DELETE` | `/evaluations/{id}` | Delete an evaluation |

### Sheet Management
| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/evaluations/{id}/sheets` | Upload answer sheets |
| `GET` | `/evaluations/{id}/sheets` | List sheets in evaluation |
| `DELETE` | `/evaluations/{id}/sheets/{sheetId}` | Delete a sheet |

### OCR Pipeline (Stage 1)
| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/evaluations/{id}/ocr/start` | Start OCR processing |
| `GET` | `/evaluations/{id}/ocr/status` | Poll OCR progress |
| `GET` | `/evaluations/{id}/ocr/result/{sheetId}` | Get OCR result |

### Text Structuring Pipeline (Stage 2)
| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/evaluations/{id}/structuring/start` | Start text structuring |
| `GET` | `/evaluations/{id}/structuring/status` | Poll structuring progress |
| `GET` | `/evaluations/{id}/structuring/result/{sheetId}` | Get structured result |

### SLM Evaluation Pipeline (Stage 3)
| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/evaluations/{id}/evaluation/start` | Start SLM evaluation |
| `GET` | `/evaluations/{id}/evaluation/status` | Poll evaluation progress |
| `GET` | `/evaluations/{id}/evaluation/result/{sheetId}` | Get evaluation result |

### Results & Export
| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/evaluations/{id}/results` | Aggregated score summary |
| `GET` | `/evaluations/{id}/results/{sheetId}` | Detailed per-sheet results |
| `POST` | `/evaluations/{id}/export/csv` | Download CSV report |
| `POST` | `/evaluations/{id}/export/pdf` | Download PDF report |

### Settings
| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/settings` | Get current settings |
| `PUT` | `/settings` | Update settings |
| `POST` | `/settings/clear-cache` | Clear Redis cache |

Full interactive documentation available at `/docs` (Swagger UI) and `/redoc`.

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- **MongoDB** (local instance on port 27017)
- **Redis** (optional — app works without it)

### Backend Setup

```bash
cd backend
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

**Start the server:**

```bash
uvicorn app.main:app --reload
```

The first run will download the SLM model (~1GB):
- Qwen2.5-0.5B (~1GB)

> **Note:** OCR uses the Mistral OCR API. Set your `MISTRAL_API_KEY`
> in the `backend/.env` file.

Server starts at: `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Dev server starts at: `http://localhost:5173`

---

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
MONGO_URI=mongodb://localhost:27017
DB_NAME=evaluation_db
REDIS_HOST=localhost
REDIS_PORT=6379
MISTRAL_API_KEY=your_mistral_api_key_here
```

---

**Status**: Full pipeline implemented — OCR (Mistral OCR) ✅ | Structuring ✅ | SLM Evaluation ✅ | Results ✅ | Export ✅