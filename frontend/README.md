# Sustainable AI Assessment Platform — Frontend

React 19 + TypeScript single-page application built with Vite and Tailwind CSS 4, providing an intuitive interface for managing offline AI assessments, live execution monitoring, and grading triage.

---

## Features

- **Evaluation Management**: Setup courses, specify grading scales, and manage student batches.
- **Answer Sheet & Rubric Uploader**: Drag-and-drop file ingestion supporting multi-page scans and institutional marking guidelines (PDF/TXT).
- **Real-Time SSE Stream Console**: Built-in macOS-style terminal console connecting to the backend's Server-Sent Events stream (`/api/evaluations/{id}/pipeline/stream`) with auto-scroll and one-click copy.
- **Stage 4 Educator Triage (Human-in-the-Loop)**: Filter view for scripts flagged with borderline scores (<60% or close to grade boundaries) or ambiguous handwriting, allowing educators to inspect and resolve scores.
- **Script Deep-Dive**: Question-by-question breakdown showing transcribed handwritten text, parsed diagrams, model rationale, and marks awarded per rubric component.
- **Flexible Export**: One-click download of aggregated class records and detailed student scorecards in CSV, PDF, and TXT formats.

---

## Route Structure

Both singular (`/evaluation/:id`) and plural (`/evaluations/:id`) route prefixes are fully supported:

| Path | Component | Purpose |
|:-----|:----------|:--------|
| `/` or `/evaluations` | `Home` | Dashboard showing active and completed evaluations |
| `/evaluation/new` | `CreateEvaluation` | Evaluation setup wizard |
| `/evaluation/:evaluationId/upload` | `UploadSheets` | Upload student answer sheets and grading rubric |
| `/evaluation/:evaluationId/process` | `ProcessEvaluation` | 5-Stage offline pipeline runner & real-time SSE stream console |
| `/evaluation/:evaluationId/results` | `ResultsOverview` | Class score distribution, summary metrics, and Stage 4 triage filters |
| `/evaluation/:evaluationId/results/:scriptId` | `ScriptDetails` | Student-level question breakdown, handwritten transcriptions, and scoring rationales |
| `/evaluation/:evaluationId/export` | `ExportResults` | Export class evaluation results to CSV, PDF, or TXT |
| `/settings` | `Settings` | System settings |

---

## Tech Stack

- **React 19**
- **TypeScript**
- **Vite 7** with Fast Refresh
- **Tailwind CSS 4**
- **React Router 7**
- **EventSource (SSE)** for real-time live execution updates

---

## Getting Started

### 1. Install Dependencies

```bash
cd capstone/frontend
npm install
```

### 2. Run the Development Server

```bash
npm run dev
```

The app will start at `http://localhost:5173`.

Vite is configured with a built-in proxy in `vite.config.ts`:
- Requests to `/api/*` are automatically forwarded to `http://localhost:8000`.

### 3. Build for Production

```bash
npm run build
```

To type-check without building:

```bash
npx tsc --noEmit
```
