# API Type System Documentation

Complete TypeScript type definitions for the Sustainable AI Assessment Platform backend API.

## Architecture Principles

- **Evaluation-scoped**: Each evaluation is an isolated processing unit
- **Async-friendly**: Long-running tasks (OCR, Structuring, Evaluation) are asynchronous
- **Status queryable**: All async operations have status endpoints
- **Clear separation**: No API mixes responsibilities
- **Offline-first**: Designed for local processing without cloud dependencies

## API Services

### 1. Evaluation Management (`evaluations.ts`)
Handles creation, listing, and deletion of evaluation sessions.

**Endpoints:**
- `POST /api/evaluations` - Create new evaluation
- `GET /api/evaluations` - List all evaluations
- `GET /api/evaluations/:id` - Get evaluation metadata
- `DELETE /api/evaluations/:id` - Delete evaluation

### 2. Answer Sheet Management (`sheets.ts`)
Manages scanned answer sheet uploads and organization.

**Endpoints:**
- `POST /api/evaluations/:id/sheets` - Bulk upload sheets
- `GET /api/evaluations/:id/sheets` - List uploaded sheets
- `DELETE /api/evaluations/:id/sheets/:sheetId` - Delete sheet

### 3. OCR Processing (`ocr.ts`)
Converts scanned images to raw text asynchronously.

**Processing States:** `PENDING → RUNNING → COMPLETED / FAILED`

**Endpoints:**
- `POST /api/evaluations/:id/ocr/start` - Start OCR pipeline
- `GET /api/evaluations/:id/ocr/status` - Get pipeline status
- `GET /api/evaluations/:id/ocr/result/:sheetId` - Get OCR result

### 4. Text Structuring (`structuring.ts`)
Transforms raw OCR text into structured algorithmic representations.

**Output includes:**
- Question identification
- Answer steps breakdown
- Algorithm detection
- Complexity analysis
- Code block extraction

**Endpoints:**
- `POST /api/evaluations/:id/structuring/start`
- `GET /api/evaluations/:id/structuring/status`
- `GET /api/evaluations/:id/structuring/result/:sheetId`

### 5. SLM Evaluation (`evaluation.ts`)
Performs rubric-based scoring using Small Language Models.

**Features:**
- Criterion-wise scoring
- Detailed feedback generation
- Confidence scores
- Strengths/improvements identification

**Endpoints:**
- `POST /api/evaluations/:id/evaluation/start`
- `GET /api/evaluations/:id/evaluation/status`
- `GET /api/evaluations/:id/evaluation/result/:sheetId`

### 6. Results & Feedback (`results.ts`)
Serves final, immutable evaluation results.

**Guarantees:**
- Read-only access
- Deterministic results
- Full rubric traceability
- Complete processing timeline

**Endpoints:**
- `GET /api/evaluations/:id/results` - Summary with statistics
- `GET /api/evaluations/:id/results/:sheetId` - Detailed student result

### 7. Export (`export.ts`)
Generates offline records in various formats.

**Formats:**
- CSV (marks only)
- PDF (marks + feedback)
- JSON (complete data)
- XLSX (spreadsheet)

**Endpoints:**
- `POST /api/evaluations/:id/export/csv`
- `POST /api/evaluations/:id/export/pdf`

### 8. Settings & System (`settings.ts`)
System-level configuration and cache management.

**Configuration areas:**
- OCR sensitivity settings
- Evaluation model parameters
- System limits and thresholds
- Cache management

**Endpoints:**
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/settings/clear-cache`

## Common Types (`common.ts`)

Standard response structures used across all APIs:
- `APIError` - Standardized error responses
- `APISuccess<T>` - Generic success wrapper
- `PaginatedResponse<T>` - Pagination support
- `APIResponse<T>` - Union of success/error

## Endpoint Configuration (`endpoints.ts`)

Centralized endpoint URL definitions with type-safe builders.

## Usage Example

```typescript
import type { CreateEvaluationRequest, CreateEvaluationResponse } from '@/api'
import { API_ENDPOINTS } from '@/api/endpoints'

const createEvaluation = async (data: CreateEvaluationRequest): Promise<CreateEvaluationResponse> => {
  const response = await fetch(API_ENDPOINTS.EVALUATION.CREATE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return response.json()
}
```

## Design Benefits

✅ **Type Safety** - Compile-time validation of all API interactions
✅ **Clear Contracts** - Well-defined request/response structures  
✅ **Scalability** - Easy to add new endpoints and types
✅ **Maintainability** - Centralized type definitions
✅ **Documentation** - Types serve as living documentation
✅ **Debugging** - Clear failure boundaries between services
