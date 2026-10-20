// ================================
// Central API Type Exports
// ================================

// Evaluation Management
export type {
    CreateEvaluationRequest,
    CreateEvaluationResponse,
    ListEvaluationsResponse,
    EvaluationMetadata,
    GetEvaluationResponse,
    DeleteEvaluationResponse,
} from './evaluations'

// Answer Sheet Management
export type {
    UploadSheetsRequest,
    UploadSheetsResponse,
    UploadedSheetInfo,
    ListSheetsResponse,
    SheetMetadata,
    DeleteSheetResponse,
} from './sheets'

// OCR Processing
export type {
    ProcessingStatus,
    StartOCRRequest,
    StartOCRResponse,
    OCRStatusResponse,
    OCRResultResponse,
    OCRResult,
} from './ocr'

// Text Structuring
export type {
    StartStructuringRequest,
    StartStructuringResponse,
    StructuringStatusResponse,
    StructuringResultResponse,
    StructuredText,
    StructuredQuestion,
    AnswerStep,
    CodeBlock,
} from './structuring'

// SLM Evaluation
export type {
    StartEvaluationRequest,
    StartEvaluationResponse,
    EvaluationStatusResponse,
    EvaluationResultResponse,
    SheetEvaluationResult,
    CriterionScore,
} from './evaluation'

// Results & Feedback
export type {
    ResultsSummaryResponse,
    EvaluationSummary,
    StudentResult,
    DetailedResultResponse,
    StudentInfo,
    DetailedEvaluation,
    RawProcessingData,
    ProcessingStep,
} from './results'

// Export
export type {
    ExportCSVRequest,
    ExportCSVResponse,
    ExportPDFRequest,
    ExportPDFResponse,
    ExportOptions,
} from './export'

// Settings & System
export type {
    GetSettingsResponse,
    SystemSettings,
    OCRSettings,
    EvaluationSettings,
    SystemConfiguration,
    CacheSettings,
    UpdateSettingsRequest,
    UpdateSettingsResponse,
    ClearCacheRequest,
    ClearCacheResponse,
} from './settings'

// Common Types
export type {
    APIError,
    APISuccess,
    PaginationParams,
    PaginatedResponse,
    APIStatus,
    HTTPMethod,
    APIResponse,
} from './common'
