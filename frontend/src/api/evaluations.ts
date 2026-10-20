// ================================
// Evaluation Management API Types
// ================================

// POST /api/evaluations - Create a new evaluation
export interface CreateEvaluationRequest {
    name: string
    subject: string
    maxMarks: number
    answerType: 'printed' | 'handwritten'
}

export interface CreateEvaluationResponse {
    success: boolean
    evaluationId: string
    message: string
}

// GET /api/evaluations - List all evaluations
export interface ListEvaluationsResponse {
    success: boolean
    evaluations: EvaluationMetadata[]
}

export interface EvaluationMetadata {
    id: string
    name: string
    subject: string
    maxMarks: number
    answerType: 'printed' | 'handwritten'
    createdAt: string
    status: 'draft' | 'in-progress' | 'completed'
    totalSheets?: number
}

// GET /api/evaluations/:evaluationId - Get evaluation metadata
export interface GetEvaluationResponse {
    success: boolean
    evaluation: EvaluationMetadata
}

// DELETE /api/evaluations/:evaluationId - Delete an evaluation
export interface DeleteEvaluationResponse {
    success: boolean
    message: string
}
