// ================================
// Results & Feedback API Types
// ================================

import type { CriterionScore } from './evaluation'

// GET /api/evaluations/:evaluationId/results - Get summary results
export interface ResultsSummaryResponse {
    success: boolean
    evaluationId: string
    summary: EvaluationSummary
    results: StudentResult[]
}

export interface EvaluationSummary {
    totalStudents: number
    averageScore: number
    highestScore: number
    lowestScore: number
    standardDeviation: number
    gradeDistribution: {
        [grade: string]: number // e.g., "A+": 5, "A": 10
    }
    completionRate: number // percentage
}

export interface StudentResult {
    sheetId: string
    rollNo: string
    studentName?: string
    totalScore: number
    maximumScore: number
    percentage: number
    grade: string
    rank?: number
    status: 'completed' | 'pending' | 'error'
}

// GET /api/evaluations/:evaluationId/results/:sheetId - Get detailed result
export interface DetailedResultResponse {
    success: boolean
    sheetId: string
    student: StudentInfo
    evaluation: DetailedEvaluation
    rawData: RawProcessingData
}

export interface StudentInfo {
    rollNo: string
    name?: string
    email?: string
}

export interface DetailedEvaluation {
    totalScore: number
    maximumScore: number
    percentage: number
    grade: string
    rank?: number
    criteria: CriterionScore[]
    overallFeedback: string
    evaluatedAt: string
    evaluatedBy: 'AI' | 'Manual' | 'Hybrid'
}

export interface RawProcessingData {
    ocrText: string
    structuredText: any // From structuring API
    processingTimeline: ProcessingStep[]
}

export interface ProcessingStep {
    stage: 'upload' | 'ocr' | 'structuring' | 'evaluation'
    status: 'completed' | 'failed'
    timestamp: string
    duration: number // milliseconds
}
