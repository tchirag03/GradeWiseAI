// ================================
// Answer Sheet Management API Types
// ================================

// POST /api/evaluations/:evaluationId/sheets - Upload answer sheets (bulk)
export interface UploadSheetsRequest {
    files: File[] // Array of image files
}

export interface UploadSheetsResponse {
    success: boolean
    uploadedSheets: UploadedSheetInfo[]
    message: string
}

export interface UploadedSheetInfo {
    sheetId: string
    fileName: string
    fileSize: number
    status: 'uploaded' | 'pending-ocr'
}

// GET /api/evaluations/:evaluationId/sheets - List uploaded sheets
export interface ListSheetsResponse {
    success: boolean
    sheets: SheetMetadata[]
}

export interface SheetMetadata {
    id: string
    evaluationId: string
    fileName: string
    fileSize: number
    filePath: string
    uploadedAt: string
    status: 'uploaded' | 'ocr-pending' | 'ocr-processing' | 'ocr-completed' | 'ocr-failed' | 'evaluated' | 'error'
}

// DELETE /api/evaluations/:evaluationId/sheets/:sheetId - Delete a specific sheet
export interface DeleteSheetResponse {
    success: boolean
    message: string
}
