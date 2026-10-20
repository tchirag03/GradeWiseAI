// Rubric criterion category
export type RubricCategory = 'excellent' | 'good' | 'satisfactory' | 'needs-improvement'

// Rubric criterion interface
export interface RubricCriterion {
    id: string
    name: string
    scoreAwarded: number
    maximumScore: number
    feedback: string
    category: RubricCategory
}
