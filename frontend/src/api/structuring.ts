// ================================
// Text Structuring API Types
// ================================

import type { ProcessingStatus } from './ocr'

// POST /api/evaluations/:evaluationId/structuring/start - Start text structuring
export interface StartStructuringRequest {
    sheetIds?: string[] // Optional: specific sheets, otherwise all OCR-completed sheets
}

export interface StartStructuringResponse {
    success: boolean
    jobId: string
    message: string
    totalSheets: number
}

// GET /api/evaluations/:evaluationId/structuring/status - Get structuring status
export interface StructuringStatusResponse {
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

// GET /api/evaluations/:evaluationId/structuring/result/:sheetId - Get structured text
export interface StructuringResultResponse {
    success: boolean
    sheetId: string
    status: ProcessingStatus
    result?: StructuredText
    error?: string
}

export interface StructuredText {
    questions: StructuredQuestion[]
    metadata: {
        totalQuestions: number
        totalSteps: number
        averageComplexity: string
    }
}

export interface StructuredQuestion {
    questionNumber: number
    questionText: string
    answer: {
        rawText: string
        structuredSteps: AnswerStep[]
        identifiedAlgorithm?: string
        complexity?: string // e.g., "O(n log n)"
        keywords: string[]
        codeBlocks?: CodeBlock[]
    }
}

export interface AnswerStep {
    stepNumber: number
    description: string
    type: 'explanation' | 'code' | 'diagram' | 'calculation'
    content: string
}

export interface CodeBlock {
    language: string
    code: string
    lineNumbers: { start: number; end: number }
}
