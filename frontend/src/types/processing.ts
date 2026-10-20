// Stage status types
export type StageStatus = 'pending' | 'in-progress' | 'completed' | 'error'

// Evaluation processing stage
export interface EvaluationStage {
    id: string
    name: string
    description: string
    status: StageStatus
    progress: number // 0-100
}
