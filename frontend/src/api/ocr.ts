// ================================
// OCR Processing API Types
// ================================

// Processing status types
export type ProcessingStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

// POST /api/evaluations/:evaluationId/ocr/start - Start OCR pipeline
export interface StartOCRRequest {
    sheetIds?: string[] // Optional: specific sheets, otherwise all sheets
    sensitivity?: 'low' | 'medium' | 'high'
}

export interface StartOCRResponse {
    success: boolean
    jobId: string
    message: string
    totalSheets: number
}

// GET /api/evaluations/:evaluationId/ocr/status - Get OCR pipeline status
export interface OCRStatusResponse {
    success: boolean
    status: ProcessingStatus
    progress: {
        total: number
        completed: number
        failed: number
        percentage: number
    }
    startedAt?: string
    completedAt?: string
    error?: string
}

// GET /api/evaluations/:evaluationId/ocr/result/:sheetId - Get OCR result for a sheet
export interface OCRResultResponse {
    success: boolean
    sheetId: string
    status: ProcessingStatus
    result?: OCRResult
    error?: string
}

export interface OCRResult {
    extractedText: string
    confidence: number // 0-100
    language: string
    processingTime: number // milliseconds
    pageCount: number
    metadata: {
        imageQuality: 'low' | 'medium' | 'high'
        textDensity: number
        detectedLanguages: string[]
    }
}
