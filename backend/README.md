# Sustainable AI Assessment Platform - Backend

**Contract-first FastAPI backend scaffold**

## 🎯 What This Is

This is a **type-safe API contract implementation** with **zero business logic**.

All endpoints are functional and return mock data to enable parallel frontend-backend development.

## 🚀 Quick Start

### Installation

```bash
cd backend
pip install -r requirements.txt
```

### Run Server

```bash
uvicorn app.main:app --reload
```

Server will start at: `http://localhost:8000`

### API Documentation

Interactive OpenAPI docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── core/
│   │   └── config.py        # Application configuration
│   ├── schemas/             # Pydantic models
│   │   ├── common.py        # Shared response types
│   │   ├── evaluation.py    # Evaluation schemas
│   │   ├── sheet.py         # Sheet schemas
│   │   └── settings.py      # Settings schemas
│   └── routers/             # API route handlers
│       ├── evaluations.py   # Evaluation CRUD
│       ├── sheets.py        # Sheet management
│       ├── ocr.py           # OCR processing
│       ├── structuring.py   # Text structuring
│       ├── slm.py           # SLM evaluation
│       ├── results.py       # Results & feedback
│       ├── export.py        # CSV/PDF export
│       └── settings.py      # System settings
```

## 🔌 API Endpoints

### Evaluation Management
- `POST /api/evaluations` - Create evaluation
- `GET /api/evaluations` - List evaluations
- `GET /api/evaluations/{id}` - Get evaluation
- `DELETE /api/evaluations/{id}` - Delete evaluation

### Answer Sheets
- `POST /api/evaluations/{id}/sheets` - Upload sheets
- `GET /api/evaluations/{id}/sheets` - List sheets
- `DELETE /api/evaluations/{id}/sheets/{sheetId}` - Delete sheet

### OCR Processing
- `POST /api/evaluations/{id}/ocr/start` - Start OCR
- `GET /api/evaluations/{id}/ocr/status` - Get status
- `GET /api/evaluations/{id}/ocr/result/{sheetId}` - Get result

### Text Structuring
- `POST /api/evaluations/{id}/structuring/start` - Start structuring
- `GET /api/evaluations/{id}/structuring/status` - Get status
- `GET /api/evaluations/{id}/structuring/result/{sheetId}` - Get result

### SLM Evaluation
- `POST /api/evaluations/{id}/evaluation/start` - Start evaluation
- `GET /api/evaluations/{id}/evaluation/status` - Get status
- `GET /api/evaluations/{id}/evaluation/result/{sheetId}` - Get result

### Results
- `GET /api/evaluations/{id}/results` - Summary
- `GET /api/evaluations/{id}/results/{sheetId}` - Detailed result

### Export
- `POST /api/evaluations/{id}/export/csv` - Export CSV
- `POST /api/evaluations/{id}/export/pdf` - Export PDF

### Settings
- `GET /api/settings` - Get settings
- `PUT /api/settings` - Update settings
- `POST /api/settings/clear-cache` - Clear cache

## ✅ What's Implemented

- ✅ All 8 API service routes
- ✅ Pydantic type validation
- ✅ OpenAPI documentation
- ✅ CORS support for frontend
- ✅ Mock responses for all endpoints

## ❌ What's Intentionally Missing

This is a **contract-only scaffold**. The following are **deliberately excluded**:

- ❌ OCR / AI / ML logic
- ❌ Database conn ections
- ❌ File storage
- ❌ Authentication
- ❌ Background workers
- ❌ Business logic

## 🎓 Development Philosophy

> **"Schemas define truth; logic comes later."**

This backend follows a contract-first approach:
1. Define API contracts with Pydantic
2. Expose all endpoints
3. Return type-safe mock data
4. Enable parallel FE-BE development
5. Inject business logic later

## 🔧 Tech Stack

- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

## 📝 Notes

- All responses are type-safe via Pydantic models
- No endpoints will raise errors
- All async operations return "pending" status
- Ready for business logic injection

## 🚦 Testing

Visit `/docs` and test all endpoints interactively through Swagger UI.

## 📞 API Response Format

All responses follow a consistent structure:

```json
{
  "success": true,
  "message": "Operation completed",
  ...additional fields
}
```

---

**Status**: Production-ready API scaffold ✅
