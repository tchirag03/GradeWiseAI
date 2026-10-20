// ================================
// SLM Evaluation API Types
// ================================

import type { ProcessingStatus } from './ocr'

// POST /api/evaluations/:evaluationId/evaluation/start - Start SLM-based evaluation
export interface StartEvaluationRequest {
    rubricId?: string // Optional: use specific rubric
    sheetIds?: string[] // Optional: specific sheets, otherwise all structured sheets
}

export interface StartEvaluationResponse {
    success: boolean
    jobId: string
    message: string
    totalSheets: number
}

// GET /api/evaluations/:evaluationId/evaluation/status - Get evaluation status
export interface EvaluationStatusResponse {
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

// GET /api/evaluations/:evaluationId/evaluation/result/:sheetId - Get evaluation result
export interface EvaluationResultResponse {
    success: boolean
    sheetId: string
    status: ProcessingStatus
    result?: SheetEvaluationResult
    error?: string
}

export interface SheetEvaluationResult {
    sheetId: string
    rollNo?: string
    studentName?: string
    totalScore: number
    maximumScore: number
    percentage: number
    grade?: string
    criteria: CriterionScore[]
    overallFeedback: string
    evaluatedAt: string
    modelVersion: string
}

export interface CriterionScore {
    criterionId: string
    criterionName: string
    scoreAwarded: number
    maximumScore: number
    percentage: number
    category: 'excellent' | 'good' | 'satisfactory' | 'needs-improvement'
    feedback: string
    strengths: string[]
    improvements: string[]
    confidenceScore: number // 0-100, AI confidence in this scoring
}
