// ================================
// Common API Response Types
// ================================

// Standard error response structure
export interface APIError {
    success: false
    error: {
        code: string
        message: string
        details?: any
        timestamp: string
    }
}

// Standard success response structure
export interface APISuccess<T = any> {
    success: true
    data: T
    message?: string
    timestamp: string
}

// Pagination types
export interface PaginationParams {
    page: number
    limit: number
    sortBy?: string
    sortOrder?: 'asc' | 'desc'
}

export interface PaginatedResponse<T> {
    success: boolean
    data: T[]
    pagination: {
        currentPage: number
        totalPages: number
        totalItems: number
        itemsPerPage: number
        hasNext: boolean
        hasPrev: boolean
    }
}

// Common status types
export type APIStatus = 'idle' | 'loading' | 'success' | 'error'

// HTTP Methods
export type HTTPMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'

// API Response wrapper
export type APIResponse<T> = APISuccess<T> | APIError
