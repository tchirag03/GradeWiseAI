# Sustainable AI Assessment Platform — Project Context

## Overview
A full-stack application designed to automate the grading of handwritten and printed student answer sheets using AI. The system processes images of answer sheets, extracts the text, structures the responses, and evaluates them against a provided rubric using a Small Language Model (SLM).

## Technology Stack
- **Backend:** FastAPI (Python)
- **Database:** MongoDB (Metadata, status tracking, evaluation results)
- **Task Queue / State:** Redis + Background Tasks
- **Frontend:** React + Vite + TypeScript + Tailwind CSS
- **AI Models:** 
  - **OCR:** Mistral OCR API (migrated from Google Cloud Vision)
  - **Structuring & Evaluation (SLM):** Qwen2.5-0.5B-Instruct (via HuggingFace)

---

## The AI Pipeline Architecture
The grading process is broken down into a 3-stage automated pipeline:

### 1. OCR Processing (`ocr.py`)
- **Action:** Takes uploaded image files and extracts raw markdown text.
- **Implementation:** Uses `mistral-ocr-latest` via the Mistral API. Images are base64 encoded and sent to the API, returning structured markdown representing the document content.

### 2. Text Structuring (`structuring.py`)
- **Action:** Takes the raw OCR text and structures it into individual Questions and Answers.
- **Implementation:** Uses the local SLM to parse the raw text into a predefined JSON schema.
- **NEW: LaTeX Preprocessing:** Added a conversion layer that transforms raw LaTeX formulas (e.g., `\frac`, `\text`, `\begin{array}`) into human-readable Markdown before evaluation, significantly improving the SLM's accuracy for mathematical content.

### 3. Rubric-Based Scoring (`slm.py`)
- **Action:** Evaluates each structured answer against the uploaded grading rubric.
- **Implementation:** The SLM evaluates each question independently, assigning marks for specific rubric components (e.g., Correctness, Clarity) and generating detailed feedback. The scores are aggregated into a final percentage and grade.

---

## Frontend Workflows & Pages

1. **Dashboard (`Home.tsx`)**: Displays all active and completed evaluations fetched from the backend. Allows deletion of evaluations.
2. **Create Evaluation (`CreateEvaluation.tsx`)**: Form to initialize a new grading session (subject, max marks, format).
3. **Upload Sheets (`UploadSheets.tsx`)**: Multipart form uploads for both the student answer sheets (images/PDFs) and the grading rubric document.
4. **Process Evaluation (`ProcessEvaluation.tsx`)**: The control center. Features live polling (`setInterval`) of the backend status endpoints to show real-time progress of the 3-stage pipeline, automatically chaining from one stage to the next.
5. **Results Overview (`ResultsOverview.tsx`)**: Aggregated view of the class performance. Displays average/highest/lowest scores and a tabular list of all students with their final grades.
6. **Script Details (`ScriptDetails.tsx`)**: Deep dive into a specific student's paper. Displays the raw Mistral OCR text side-by-side with the AI's per-question score breakdown and feedback.
7. **Export Results (`ExportResults.tsx`)**: Generates and downloads a consolidated CSV or PDF report of the entire evaluation directly from the backend.

---

## Completed Milestones (History)

### Phase 1: OCR Migration & Pipeline Orchestration
- **Replaced Google Cloud Vision with Mistral OCR API**: Refactored `ocr_service.py` and `ocr.py` to use base64 encoding and the `mistralai` SDK. Cleaned up old GCP dependencies.
- **Frontend-Backend Proxy Configuration**: Set up Vite proxy to route `/api` to the FastAPI backend running on port `8000`.
- **Real File Uploads**: Replaced mock uploads with actual `FormData` multipart requests for answer sheets and rubrics.
- **Live Pipeline Polling**: Replaced mock timeout simulations with real API polling for the pipeline stages, ensuring accurate progress bars and status updates.

### Phase 2: Results & Reporting Integration
- **Cleaned Up Navigation**: Removed the obsolete "Rubric Builder" route, as rubrics are now uploaded as files during the sheet upload phase.
- **Wired Results Overview**: Connected the summary page to the real aggregated backend data (`GET /results`).
- **Wired Script Details**: Connected the detailed view to fetch both the raw OCR text and the per-question SLM evaluation feedback.
- **Wired Exports**: Connected the CSV/PDF export buttons to the backend endpoints, properly handling binary blob downloads in the browser.
- **Fixed Validation Bugs**: Resolved a 500 Internal Server Error caused by a strict Pydantic Literal schema mismatch (`SheetStatus`) during the pipeline evaluation stage.

---

> [!NOTE]
> *This document will be updated continuously as new features are added, architectures change, or significant bugs are resolved.*
