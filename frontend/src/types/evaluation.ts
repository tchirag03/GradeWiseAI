// Evaluation data types
export interface Evaluation {
    id: string
    name: string
    courseSubject: string
    maximumMarks: number
    answerType: 'printed' | 'handwritten'
    createdAt: string
    status: 'draft' | 'in-progress' | 'completed'
    totalSheets?: number
}

// Form data for creating evaluations
export interface EvaluationFormData {
    evaluationName: string
    courseSubject: string
    maximumMarks: string
    answerType: 'printed' | 'handwritten'
}

// Evaluation status types
export type EvaluationStatus = 'not-started' | 'processing' | 'completed' | 'error'
