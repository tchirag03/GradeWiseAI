// ================================
// API Endpoints Configuration
// ================================

/**
 * Complete API endpoint definitions for Sustainable AI Assessment Platform
 * Following offline-first, async-friendly architecture
 */

const API_BASE_URL = '/api'

// ================================
// Evaluation Management APIs
// ================================

export const EVALUATION_ENDPOINTS = {
    // Create a new evaluation
    CREATE: `${API_BASE_URL}/evaluations`,

    // List all evaluations
    LIST: `${API_BASE_URL}/evaluations`,

    // Get evaluation metadata
    GET: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}`,

    // Delete an evaluation
    DELETE: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}`,
} as const

// ================================
// Answer Sheet Management APIs
// ================================

export const SHEET_ENDPOINTS = {
    // Upload answer sheets (bulk)
    UPLOAD: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/sheets`,

    // List uploaded sheets
    LIST: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/sheets`,

    // Delete a specific sheet
    DELETE: (evaluationId: string, sheetId: string) =>
        `${API_BASE_URL}/evaluations/${evaluationId}/sheets/${sheetId}`,
} as const

// ================================
// OCR Processing APIs
// ================================

export const OCR_ENDPOINTS = {
    // Start OCR pipeline
    START: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/ocr/start`,

    // Get OCR pipeline status
    STATUS: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/ocr/status`,

    // Get OCR result for a sheet
    RESULT: (evaluationId: string, sheetId: string) =>
        `${API_BASE_URL}/evaluations/${evaluationId}/ocr/result/${sheetId}`,
} as const

// ================================
// Text Structuring APIs
// ================================

export const STRUCTURING_ENDPOINTS = {
    // Start text structuring
    START: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/structuring/start`,

    // Get structuring status
    STATUS: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/structuring/status`,

    // Get structured text for a sheet
    RESULT: (evaluationId: string, sheetId: string) =>
        `${API_BASE_URL}/evaluations/${evaluationId}/structuring/result/${sheetId}`,
} as const

// ================================
// SLM Evaluation APIs
// ================================

export const EVALUATION_API_ENDPOINTS = {
    // Start SLM-based evaluation
    START: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/evaluation/start`,

    // Get evaluation status
    STATUS: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/evaluation/status`,

    // Get evaluation result for a sheet
    RESULT: (evaluationId: string, sheetId: string) =>
        `${API_BASE_URL}/evaluations/${evaluationId}/evaluation/result/${sheetId}`,
} as const

// ================================
// Results & Feedback APIs
// ================================

export const RESULTS_ENDPOINTS = {
    // Get summary results for evaluation
    SUMMARY: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/results`,

    // Get detailed result for a sheet
    DETAIL: (evaluationId: string, sheetId: string) =>
        `${API_BASE_URL}/evaluations/${evaluationId}/results/${sheetId}`,

    // Stage 4 Review Queue
    REVIEW_QUEUE: (evaluationId: string) =>
        `${API_BASE_URL}/evaluations/${evaluationId}/review_queue`,

    // Stage 4 Resolve Review
    RESOLVE_REVIEW: (evaluationId: string, sheetId: string) =>
        `${API_BASE_URL}/evaluations/${evaluationId}/review_queue/${sheetId}/resolve`,
} as const

// ================================
// Offline 5-Stage Pipeline APIs
// ================================

export const PIPELINE_ENDPOINTS = {
    // Start unified offline pipeline
    START: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/pipeline/start`,

    // Get pipeline status
    STATUS: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/pipeline/status`,
} as const

// ================================
// Export APIs
// ================================

export const EXPORT_ENDPOINTS = {
    // Export results as CSV
    CSV: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/export/csv`,

    // Export results as PDF
    PDF: (evaluationId: string) => `${API_BASE_URL}/evaluations/${evaluationId}/export/pdf`,
} as const

// ================================
// Settings & System APIs
// ================================

export const SETTINGS_ENDPOINTS = {
    // Get system settings
    GET: `${API_BASE_URL}/settings`,

    // Update system settings
    UPDATE: `${API_BASE_URL}/settings`,

    // Clear system cache
    CLEAR_CACHE: `${API_BASE_URL}/settings/clear-cache`,
} as const

// ================================
// All Endpoints Export
// ================================

export const API_ENDPOINTS = {
    EVALUATION: EVALUATION_ENDPOINTS,
    SHEET: SHEET_ENDPOINTS,
    PIPELINE: PIPELINE_ENDPOINTS,
    OCR: OCR_ENDPOINTS,
    STRUCTURING: STRUCTURING_ENDPOINTS,
    EVALUATION_API: EVALUATION_API_ENDPOINTS,
    RESULTS: RESULTS_ENDPOINTS,
    EXPORT: EXPORT_ENDPOINTS,
    SETTINGS: SETTINGS_ENDPOINTS,
} as const

export default API_ENDPOINTS
