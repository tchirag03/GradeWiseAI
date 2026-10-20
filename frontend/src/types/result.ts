// Result status types
export type ResultStatus = 'completed' | 'error' | 'pending' | 'review-needed'

export interface SheetCrop {
    crop_id: string
    crop_type: 'text' | 'figure' | 'table' | 'math' | 'unknown'
    crop_path: string
    bbox: number[]
    transcription?: string
    diagram_description?: string
}

// Script evaluation result
export interface ScriptResult {
    scriptId: string
    rollNo?: string
    studentName: string
    fileName?: string
    totalMarks: number
    maximumMarks: number
    status: ResultStatus
    percentage: number
    grade?: string
    needsHumanReview?: boolean
    reviewReasons?: string[]
}
