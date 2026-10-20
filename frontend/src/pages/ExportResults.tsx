import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { ExportFormat } from '@/types'
import { get } from '@/api/client'

// Minimal interface for an Evaluation
interface EvaluationDetails {
  name: string
}

interface ListSheetsApiResponse {
  success: boolean
  sheets: { id: string; status: string }[]
}

function ExportResults() {
  const { evaluationId } = useParams<{ evaluationId: string }>()

  // State management
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('csv')
  const [isExporting, setIsExporting] = useState(false)
  const [exportComplete, setExportComplete] = useState(false)
  const [exportLocation, setExportLocation] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [includeDetails, setIncludeDetails] = useState(false)

  // Real data
  const [evaluationName, setEvaluationName] = useState('Loading...')
  const [totalScripts, setTotalScripts] = useState(0)

  useEffect(() => {
    if (!evaluationId) return

    const loadData = async () => {
      try {
        const evalDetails = await get<EvaluationDetails>(`/evaluations/${evaluationId}`)
        setEvaluationName(evalDetails.name)

        const sheetsData = await get<ListSheetsApiResponse>(`/evaluations/${evaluationId}/sheets`)
        const completed = sheetsData.sheets.filter(s => s.status === 'evaluation-completed').length
        setTotalScripts(completed)
      } catch (err: any) {
        console.error('Failed to load details for export:', err)
      }
    }

    loadData()
  }, [evaluationId])

  const handleFormatChange = (format: ExportFormat) => {
    setSelectedFormat(format)
    setIncludeDetails(format === 'pdf')
  }

  // Handle actual file export via backend
  const handleExport = async () => {
    if (!evaluationId) return

    setIsExporting(true)
    setExportComplete(false)
    setError(null)

    try {
      // We use raw fetch here instead of api client because we need a Blob, not JSON
      const urlPath = `/api/evaluations/${evaluationId}/export/${selectedFormat}${includeDetails ? '?include_details=true' : ''}`
      const response = await fetch(urlPath, {
        method: 'POST',
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || errData.message || 'Export failed on the server')
      }

      // Convert response to blob
      const blob = await response.blob()

      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob)

      // Safely format the filename
      const safeName = evaluationName.replace(/[^a-z0-9]/gi, '_').toLowerCase()
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 10)
      const fileName = `${safeName}_results_${timestamp}.${selectedFormat}`

      // Create a temporary link element to trigger the download
      const a = document.createElement('a')
      a.href = url
      a.download = fileName
      document.body.appendChild(a)
      a.click()

      // Cleanup
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

      setExportLocation(fileName)
      setExportComplete(true)
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred during export')
    } finally {
      setIsExporting(false)
    }
  }

  // Get format icon
  const getFormatIcon = (format: ExportFormat) => {
    if (format === 'csv') {
      return (
        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      )
    }
    return (
      <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
      </svg>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Export Results</h1>
        <p className="text-slate-600">
          Download evaluation results for offline record-keeping
        </p>
      </div>

      {/* Evaluation Info */}
      <div className="bg-white border-2 border-slate-200 rounded-lg p-6 mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4">Evaluation Details</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-slate-500 mb-1">Evaluation Name</p>
            <p className="font-semibold text-slate-800">{evaluationName}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500 mb-1">Evaluation ID</p>
            <p className="font-semibold text-slate-800 font-mono text-sm">{evaluationId}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500 mb-1">Evaluated Scripts</p>
            <p className="font-semibold text-slate-800">{totalScripts} answer sheets</p>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8 flex items-center gap-3">
          <svg className="w-5 h-5 text-red-600 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <p className="text-sm text-red-800 font-medium">{error}</p>
        </div>
      )}

      {/* Export Configuration */}
      <div className="bg-white border-2 border-slate-200 rounded-lg p-6 mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-6">Export Configuration</h2>

        {/* Format Selection */}
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-3">
            Export Format
          </label>
          <div className="grid md:grid-cols-2 gap-4">
            {/* CSV Option */}
            <label
              className={`border-2 rounded-lg p-4 cursor-pointer transition-all duration-200 ${selectedFormat === 'csv'
                ? 'border-blue-600 bg-blue-50'
                : 'border-slate-200 hover:border-slate-300'
                }`}
            >
              <input
                type="radio"
                name="format"
                value="csv"
                checked={selectedFormat === 'csv'}
                onChange={() => handleFormatChange('csv')}
                className="sr-only"
              />
              <div className="flex items-start gap-3">
                <div className={`${selectedFormat === 'csv' ? 'text-blue-600' : 'text-slate-400'}`}>
                  {getFormatIcon('csv')}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-bold text-slate-800">CSV Spreadsheet</span>
                    {selectedFormat === 'csv' && (
                      <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  <p className="text-sm text-slate-600">
                    Spreadsheet format with marks. Toggle explainability for per-question breakdown.
                  </p>
                  <div className="mt-2 text-xs text-slate-500">
                    Includes: File Name, Total Marks, Percentage, Grade + per-question scores & feedback when detailed
                  </div>
                </div>
              </div>
            </label>

            {/* PDF Option */}
            <label
              className={`border-2 rounded-lg p-4 cursor-pointer transition-all duration-200 ${selectedFormat === 'pdf'
                ? 'border-blue-600 bg-blue-50'
                : 'border-slate-200 hover:border-slate-300'
                }`}
            >
              <input
                type="radio"
                name="format"
                value="pdf"
                checked={selectedFormat === 'pdf'}
                onChange={() => handleFormatChange('pdf')}
                className="sr-only"
              />
              <div className="flex items-start gap-3">
                <div className={`${selectedFormat === 'pdf' ? 'text-blue-600' : 'text-slate-400'}`}>
                  {getFormatIcon('pdf')}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-bold text-slate-800">PDF Report</span>
                    {selectedFormat === 'pdf' && (
                      <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  <p className="text-sm text-slate-600">
                    Professional document with marks and tabular overview. Printable and shareable. Toggle explainability for per-student rubric assessment pages.
                  </p>
                  <div className="mt-2 text-xs text-slate-500">
                    Includes: Consolidated evaluation summary table
                  </div>
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Explainability Toggle */}
        <div className="mt-6 border-t border-slate-200 pt-6">
          <label className="flex items-start gap-3 cursor-pointer group w-fit">
            <div className="flex items-center h-5">
              <input
                type="checkbox"
                checked={includeDetails}
                onChange={(e) => setIncludeDetails(e.target.checked)}
                className="w-4 h-4 text-blue-600 bg-slate-100 border-slate-300 rounded focus:ring-blue-500"
              />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-800 group-hover:text-blue-700 transition-colors">
                Include AI Explainability Details
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Adds per-question rubric breakdown, AI feedback, and evaluation method to the export
              </p>
            </div>
          </label>
        </div>
      </div>

      {/* Export Action */}
      <div className="flex items-center justify-between mb-8">
        <div className="text-sm text-slate-600 font-medium">
          {selectedFormat === 'csv' ? '📊 CSV' : '📄 PDF'} format • 1 file containing {totalScripts} student records
        </div>

        <button
          onClick={handleExport}
          disabled={isExporting || totalScripts === 0}
          className={`px-8 py-3 rounded-lg font-semibold transition-all duration-200 flex items-center gap-2 ${isExporting || totalScripts === 0
            ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg'
            }`}
        >
          {isExporting ? (
            <>
              <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Exporting...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Export Results
            </>
          )}
        </button>
      </div>

      {/* Success Message */}
      {exportComplete && (
        <div className="bg-green-50 border-2 border-green-200 rounded-lg p-6 mb-8">
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 text-green-600 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-green-800 mb-2">Export Downloaded Successfully!</h3>
              <p className="text-sm text-green-700 mb-3">
                Your {selectedFormat.toUpperCase()} file has been generated and saved to your Downloads folder.
              </p>
              <div className="bg-white border border-green-200 rounded p-3">
                <p className="text-xs text-slate-500 mb-1">File Name:</p>
                <p className="text-sm font-mono text-slate-800 break-all">{exportLocation}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex gap-3">
          <svg className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div className="text-sm text-blue-800">
            <p className="font-semibold mb-1">Offline Export</p>
            <p>All exports are generated locally. Your data never leaves your device, ensuring complete privacy and data security.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ExportResults
