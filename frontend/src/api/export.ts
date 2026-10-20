// ================================
// Export API Types
// ================================

// POST /api/evaluations/:evaluationId/export/csv - Export results as CSV
export interface ExportCSVRequest {
    scope?: 'all' | 'summary' | 'detailed'
    includeFields?: string[] // Optional: specific fields to include
}

export interface ExportCSVResponse {
    success: boolean
    fileUrl: string // Local file path or download URL
    fileName: string
    fileSize: number
    recordCount: number
    generatedAt: string
}

// POST /api/evaluations/:evaluationId/export/pdf - Export results as PDF
export interface ExportPDFRequest {
    scope: 'entire' | 'individual' // Entire evaluation or individual student reports
    template?: 'standard' | 'detailed' | 'summary'
    includeRubric?: boolean
    includeFeedback?: boolean
    includeOCRText?: boolean
    studentIds?: string[] // For individual export
}

export interface ExportPDFResponse {
    success: boolean
    fileUrl: string // Local file path or download URL (ZIP if multiple PDFs)
    fileName: string
    fileSize: number
    pageCount?: number
    fileCount?: number // For ZIP archives
    generatedAt: string
}

// Common export options
export interface ExportOptions {
    format: 'csv' | 'pdf' | 'json' | 'xlsx'
    compression?: 'none' | 'zip'
    includeTimestamp?: boolean
    customFileName?: string
}
