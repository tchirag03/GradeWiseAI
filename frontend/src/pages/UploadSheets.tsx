import { useState, useRef, useEffect } from 'react'
import type { DragEvent, ChangeEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { get, post, upload, del } from '@/api/client'

interface SheetInfo {
  id: string
  name: string
  size: number
  status: 'uploading' | 'uploaded' | 'error'
  error?: string
  page_count?: number
  is_bundle?: boolean
  pages?: { page_number: number; file_name: string; file_size: number }[]
}

interface RubricInfo {
  name: string
  size: number
  status: 'uploading' | 'uploaded' | 'error'
}

interface ListSheetsApiResponse {
  success: boolean
  sheets: {
    id: string
    file_name: string
    file_size: number
    status: string
    page_count?: number
    is_bundle?: boolean
    pages?: { page_number: number; file_name: string; file_size: number }[]
  }[]
}

function UploadSheets() {
  const { evaluationId } = useParams<{ evaluationId: string }>()
  const navigate = useNavigate()
  const [uploadedFiles, setUploadedFiles] = useState<SheetInfo[]>([])
  const [submissionMode, setSubmissionMode] = useState<'single_script' | 'individual_files'>('single_script')
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Rubric upload state
  const [rubricFile, setRubricFile] = useState<RubricInfo | null>(null)
  const rubricInputRef = useRef<HTMLInputElement>(null)

  // Load existing sheets and rubric on mount
  useEffect(() => {
    if (!evaluationId) return
    const loadData = async () => {
      try {
        // Fetch sheets
        const sheetsData = await get<ListSheetsApiResponse>(`/evaluations/${evaluationId}/sheets`)
        setUploadedFiles(
          sheetsData.sheets.map((s) => ({
            id: s.id,
            name: s.file_name,
            size: s.file_size,
            status: 'uploaded' as const,
            page_count: s.page_count,
            is_bundle: s.is_bundle,
            pages: s.pages,
          }))
        )

        // Fetch rubric
        try {
          const rubricData = await get<{ success: boolean; rubric: any }>(`/evaluations/${evaluationId}/rubric`)
          if (rubricData.success && rubricData.rubric) {
            setRubricFile(rubricData.rubric)
          }
        } catch {
          // No rubric yet
        }
      } catch {
        // Error loading sheets
      }
    }
    loadData()
  }, [evaluationId])

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  // Upload files to the backend
  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0 || !evaluationId) return

    setIsUploading(true)

    // Add files with 'uploading' status immediately for UI feedback
    const newFiles: SheetInfo[] = Array.from(files).map((file) => ({
      id: `temp-${file.name}-${Date.now()}`,
      name: file.name,
      size: file.size,
      status: 'uploading' as const,
    }))
    setUploadedFiles((prev) => [...prev, ...newFiles])

    try {
      const formData = new FormData()
      Array.from(files).forEach((file) => {
        formData.append('files', file)
      })

      await upload<{
        success: boolean
        uploaded_sheets: { sheet_id: string; file_name: string; file_size: number; status: string; page_count?: number; is_bundle?: boolean }[]
        message: string
      }>(`/evaluations/${evaluationId}/sheets?mode=${submissionMode}`, formData)

      // Fetch fresh list from server to get accurate bundle & page counts
      const sheetsData = await get<ListSheetsApiResponse>(`/evaluations/${evaluationId}/sheets`)
      setUploadedFiles(
        sheetsData.sheets.map((s) => ({
          id: s.id,
          name: s.file_name,
          size: s.file_size,
          status: 'uploaded' as const,
          page_count: s.page_count,
          is_bundle: s.is_bundle,
          pages: s.pages,
        }))
      )
    } catch (err: any) {
      // Mark all temp files as errored
      setUploadedFiles((prev) =>
        prev.map((f) =>
          f.id.startsWith('temp-')
            ? { ...f, status: 'error' as const, error: err.message }
            : f
        )
      )
    } finally {
      setIsUploading(false)
    }
  }

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files)
    // Reset input so the same file can be re-selected
    if (e.target) e.target.value = ''
  }

  const handleRemoveFile = async (fileId: string) => {
    // Optimistic UI update
    setUploadedFiles((prev) => prev.filter((file) => file.id !== fileId))

    if (!evaluationId || fileId.startsWith('temp-')) return

    try {
      await del(`/evaluations/${evaluationId}/sheets/${fileId}`)
    } catch (err: any) {
      console.error('Failed to delete file from server:', err)
      // Optional: Could revert UI state here, but for simplicity we log the error
    }
  }

  const handleBrowseClick = () => {
    fileInputRef.current?.click()
  }

  // Rubric file upload
  const handleRubricFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !evaluationId) return

    setRubricFile({ name: file.name, size: file.size, status: 'uploading' })

    try {
      const formData = new FormData()
      formData.append('file', file)
      await upload(`/evaluations/${evaluationId}/rubric`, formData)
      setRubricFile({ name: file.name, size: file.size, status: 'uploaded' })
    } catch {
      setRubricFile({ name: file.name, size: file.size, status: 'error' })
    }
  }

  const handleRubricBrowseClick = () => {
    rubricInputRef.current?.click()
  }

  const handleRemoveRubric = async () => {
    if (!evaluationId || !rubricFile || rubricFile.status !== 'uploaded') {
      setRubricFile(null)
      return
    }

    try {
      await del(`/evaluations/${evaluationId}/rubric`)
      setRubricFile(null)
      if (rubricInputRef.current) {
        rubricInputRef.current.value = ''
      }
    } catch (err) {
      console.error('Failed to remove rubric:', err)
    }
  }

  const handleClearAll = async () => {
    if (!evaluationId || realSheets.length === 0) {
      setUploadedFiles([])
      return
    }

    const confirmClear = window.confirm(`Are you sure you want to delete all ${realSheets.length} uploaded files?`)
    if (!confirmClear) return

    try {
      // Delete each file sequentially or in parallel
      await Promise.all(realSheets.map(file => del(`/evaluations/${evaluationId}/sheets/${file.id}`)))
      setUploadedFiles([])
    } catch (err) {
      console.error('Failed to clear all files:', err)
      // Refresh list to show what's actually left
      const data = await get<ListSheetsApiResponse>(`/evaluations/${evaluationId}/sheets`)
      setUploadedFiles(data.sheets.map(s => ({
        id: s.id,
        name: s.file_name,
        size: s.file_size,
        status: 'uploaded'
      })))
    }
  }


  const handleBundleAll = async () => {
    if (!evaluationId) return
    try {
      await post(`/evaluations/${evaluationId}/sheets/bundle`, {})
      const sheetsData = await get<ListSheetsApiResponse>(`/evaluations/${evaluationId}/sheets`)
      setUploadedFiles(
        sheetsData.sheets.map((s) => ({
          id: s.id,
          name: s.file_name,
          size: s.file_size,
          status: 'uploaded' as const,
          page_count: s.page_count,
          is_bundle: s.is_bundle,
          pages: s.pages,
        }))
      )
    } catch (err: any) {
      console.error('Failed to bundle sheets:', err)
    }
  }

  const handleUnbundleAll = async () => {
    if (!evaluationId) return
    try {
      await post(`/evaluations/${evaluationId}/sheets/unbundle`, {})
      const sheetsData = await get<ListSheetsApiResponse>(`/evaluations/${evaluationId}/sheets`)
      setUploadedFiles(
        sheetsData.sheets.map((s) => ({
          id: s.id,
          name: s.file_name,
          size: s.file_size,
          status: 'uploaded' as const,
          page_count: s.page_count,
          is_bundle: s.is_bundle,
          pages: s.pages,
        }))
      )
    } catch (err: any) {
      console.error('Failed to unbundle sheets:', err)
    }
  }

  const realSheets = uploadedFiles.filter((f) => f.status === 'uploaded')

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Upload Answer Sheets</h1>
        <p className="text-slate-600">
          Evaluation ID: <span className="font-semibold text-slate-800 font-mono text-sm">{evaluationId}</span>
        </p>
      </div>

      {/* Rubric Upload Section */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-2">Upload Evaluation Rubric & Model Answer</h2>
        <p className="text-sm text-slate-500 mb-4">
          Upload your grading criteria, ideal model answers, and mark band descriptors. Having an exact answer key prevents grading hallucinations.
        </p>

        {!rubricFile ? (
          <div className="bg-white border-2 border-slate-200 rounded-lg p-6">
            <input
              ref={rubricInputRef}
              type="file"
              accept=".pdf,.doc,.docx,.txt"
              onChange={handleRubricFileChange}
              className="hidden"
            />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <svg className="w-10 h-10 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div>
                  <p className="font-semibold text-slate-700">Upload rubric & model answer document</p>
                  <p className="text-sm text-slate-500">PDF, DOC, DOCX, or TXT files accepted</p>
                </div>
              </div>
              <button
                onClick={handleRubricBrowseClick}
                className="bg-slate-700 hover:bg-slate-800 text-white font-semibold py-2 px-6 rounded-lg transition-colors duration-200"
              >
                Choose File
              </button>
            </div>
          </div>
        ) : (
          <div className={`bg-white border-2 rounded-lg p-6 ${rubricFile.status === 'uploaded' ? 'border-green-200' : rubricFile.status === 'error' ? 'border-red-200' : 'border-blue-200'}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded flex items-center justify-center shrink-0 ${rubricFile.status === 'uploaded' ? 'bg-green-100' : rubricFile.status === 'error' ? 'bg-red-100' : 'bg-blue-100'}`}>
                  {rubricFile.status === 'uploading' ? (
                    <svg className="w-6 h-6 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <svg className={`w-6 h-6 ${rubricFile.status === 'uploaded' ? 'text-green-600' : 'text-red-600'}`} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-slate-800">{rubricFile.name}</p>
                  <p className="text-sm text-slate-500">{formatFileSize(rubricFile.size)}</p>
                </div>
              </div>
              <button
                onClick={handleRemoveRubric}
                className="text-red-600 hover:text-red-700 hover:bg-red-50 p-2 rounded transition-colors"
                title="Remove rubric"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        )}
      </div>


      {/* Answer Sheets Upload Section */}
      <div className="mb-6">
        <h2 className="text-xl font-bold text-slate-800 mb-2">Upload Answer Sheets</h2>
        <p className="text-sm text-slate-500 mb-4">
          Choose whether your uploaded files represent one student's multi-page answer script or multiple individual student scripts.
        </p>

        {/* Submission Mode Selector */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-4">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2.5">
            Submission Structure
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setSubmissionMode('single_script')}
              className={`p-3.5 rounded-lg border text-left transition-all ${
                submissionMode === 'single_script'
                  ? 'border-blue-500 bg-blue-50/80 shadow-xs ring-1 ring-blue-500/20'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex items-center gap-2 font-semibold text-slate-800 text-sm">
                <span className="text-base">📄</span> Single Student (Multi-Page)
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Combine all uploaded photos/pages into 1 continuous answer script evaluated together.
              </div>
            </button>

            <button
              type="button"
              onClick={() => setSubmissionMode('individual_files')}
              className={`p-3.5 rounded-lg border text-left transition-all ${
                submissionMode === 'individual_files'
                  ? 'border-blue-500 bg-blue-50/80 shadow-xs ring-1 ring-blue-500/20'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex items-center gap-2 font-semibold text-slate-800 text-sm">
                <span className="text-base">👥</span> Class Batch (1 File = 1 Student)
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Each uploaded image or PDF belongs to a separate student.
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Upload Area */}
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-3 border-dashed rounded-lg p-12 text-center transition-all duration-200 ${isDragging
          ? 'border-blue-600 bg-blue-50'
          : 'border-slate-300 bg-white hover:border-slate-400'
          }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,.pdf"
          onChange={handleFileInputChange}
          className="hidden"
        />

        <div className="flex flex-col items-center">
          <svg
            className={`w-16 h-16 mb-4 ${isDragging ? 'text-blue-600' : 'text-slate-400'}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>

          <h3 className="text-xl font-semibold text-slate-800 mb-2">
            {isDragging ? 'Drop files here' : 'Drag and drop files here'}
          </h3>
          <p className="text-slate-600 mb-4">or</p>

          <button
            onClick={handleBrowseClick}
            disabled={isUploading}
            className={`font-semibold py-3 px-8 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg ${
              isUploading
                ? 'bg-blue-400 cursor-not-allowed text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            {isUploading ? 'Uploading...' : 'Browse Files'}
          </button>

          <p className="text-sm text-slate-500 mt-4">
            Supported formats: Images (PNG, JPG, JPEG) and PDF files
          </p>
        </div>
      </div>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-slate-800">
                Uploaded Scripts ({realSheets.length})
              </h2>
              {realSheets.length > 1 && (
                <button
                  type="button"
                  onClick={handleBundleAll}
                  className="text-xs font-semibold px-2.5 py-1 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 transition-colors"
                  title="Combine all into 1 multi-page script"
                >
                  🔗 Combine all into 1 Script
                </button>
              )}
              {realSheets.some((f) => f.is_bundle && f.page_count && f.page_count > 1) && (
                <button
                  type="button"
                  onClick={handleUnbundleAll}
                  className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-300 hover:bg-slate-200 transition-colors"
                  title="Split bundle into individual pages"
                >
                  ✂️ Split into Individual Pages
                </button>
              )}
            </div>
            {uploadedFiles.length > 0 && (
              <button
                onClick={handleClearAll}
                className="text-sm text-red-600 hover:text-red-700 font-semibold"
              >
                Clear All
              </button>
            )}
          </div>

          <div className="bg-white border-2 border-slate-200 rounded-lg overflow-hidden">
            {uploadedFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-4 border-b border-slate-200 last:border-b-0 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-4 flex-1">
                  {/* File Icon */}
                  <div className={`w-10 h-10 rounded flex items-center justify-center shrink-0 ${
                    file.status === 'error' ? 'bg-red-100' : file.status === 'uploading' ? 'bg-blue-100' : 'bg-green-100'
                  }`}>
                    {file.status === 'uploading' ? (
                      <svg className="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : (
                      <svg className={`w-6 h-6 ${file.status === 'error' ? 'text-red-600' : 'text-green-600'}`} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>

                  {/* File Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-slate-800 truncate">{file.name}</p>
                      {file.is_bundle && file.page_count && file.page_count > 1 && (
                        <span className="shrink-0 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-100 text-indigo-800 border border-indigo-200">
                          📄 {file.page_count} Pages Combined
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-500">
                      {formatFileSize(file.size)}
                      {file.pages && file.pages.length > 1 && (
                        <span className="text-slate-400 ml-2">
                          (Pages: {file.pages.map(p => p.file_name).join(', ')})
                        </span>
                      )}
                      {file.status === 'error' && (
                        <span className="text-red-600 ml-2">— Upload failed</span>
                      )}
                      {file.status === 'uploading' && (
                        <span className="text-blue-600 ml-2">— Uploading...</span>
                      )}
                    </p>
                  </div>
                </div>

                {/* Remove Button */}
                <button
                  onClick={() => handleRemoveFile(file.id)}
                  className="ml-4 text-red-600 hover:text-red-700 hover:bg-red-50 p-2 rounded transition-colors"
                  title="Remove file"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            ))}
          </div>

          {/* Next Steps */}
          {realSheets.length > 0 && (
            <div className="mt-6 flex gap-4">
              <button
                onClick={() => navigate(`/evaluation/${evaluationId}/process`)}
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-8 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg"
              >
                Proceed to Process →
              </button>
              <div className="flex items-center">
                <p className="text-sm text-green-700 font-medium">
                  ✅ {realSheets.length} file(s) ready for processing
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default UploadSheets
