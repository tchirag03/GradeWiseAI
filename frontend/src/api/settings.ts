// ================================
// Settings & System API Types
// ================================

// GET /api/settings - Get system settings
export interface GetSettingsResponse {
    success: boolean
    settings: SystemSettings
}

export interface SystemSettings {
    ocr: OCRSettings
    evaluation: EvaluationSettings
    system: SystemConfiguration
    cache: CacheSettings
}

export interface OCRSettings {
    sensitivity: 'low' | 'medium' | 'high'
    language: string
    enhanceImage: boolean
    deskew: boolean
    removeNoise: boolean
}

export interface EvaluationSettings {
    modelVersion: string
    temperature: number // AI model temperature
    maxTokens: number
    confidenceThreshold: number // Minimum confidence for auto-grading
    enableExplanations: boolean
}

export interface SystemConfiguration {
    maxConcurrentJobs: number
    maxFileSize: number // bytes
    allowedFileTypes: string[]
    dataRetentionDays: number
    enableLogging: boolean
    logLevel: 'debug' | 'info' | 'warn' | 'error'
}

export interface CacheSettings {
    enabled: boolean
    maxSize: number // MB
    ttl: number // seconds
    strategy: 'lru' | 'lfu' | 'fifo'
}

// PUT /api/settings - Update system settings
export interface UpdateSettingsRequest {
    ocr?: Partial<OCRSettings>
    evaluation?: Partial<EvaluationSettings>
    system?: Partial<SystemConfiguration>
    cache?: Partial<CacheSettings>
}

export interface UpdateSettingsResponse {
    success: boolean
    message: string
    updatedSettings: SystemSettings
}

// POST /api/settings/clear-cache - Clear system cache
export interface ClearCacheRequest {
    scope?: 'all' | 'ocr' | 'evaluation' | 'results' // Optional: specific cache to clear
}

export interface ClearCacheResponse {
    success: boolean
    message: string
    clearedSize: number // bytes
    itemsCleared: number
}
