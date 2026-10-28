import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { get } from '@/api/client'

// Backend API response types
interface ResultSummary {
  total_students: number
  average_score: number
  highest_score: number
  lowest_score: number
  average_percentage: number
}

interface ScriptResult {
  _id: string
  student_name: string
  file_name: string
  total_score: number
  max_score: number
  percentage: number
  grade: string
  status?: string
  needs_human_review?: boolean
  review_reasons?: string[]
  top_loss_component?: string
  feedback_summary?: string
  evaluation_method?: string
}

interface ResultsOverviewApiResponse {
  success: boolean
  evaluation_id: string
  summary: ResultSummary
  results: ScriptResult[]
}

interface EvaluationDetails {
  name: string
}

function ResultsOverview() {
  const { evaluationId } = useParams<{ evaluationId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [evaluationName, setEvaluationName] = useState<string>('Loading...')

  const [summary, setSummary] = useState<ResultSummary>({
    total_students: 0,
    average_score: 0,
    highest_score: 0,
    lowest_score: 0,
    average_percentage: 0,
  })
  const [results, setResults] = useState<ScriptResult[]>([])
  
  // Tab filter: 'all' | 'review' | 'approved'
  const initialTab = (searchParams.get('tab') as 'all' | 'review' | 'approved') || 'all'
  const [activeTab, setActiveTab] = useState<'all' | 'review' | 'approved'>(initialTab)

  const [hoveredResultId, setHoveredResultId] = useState<string | null>(null)

  useEffect(() => {
    if (!evaluationId) return

    const loadData = async () => {
      setIsLoading(true)
      try {
        const evalDetails = await get<EvaluationDetails>(`/evaluations/${evaluationId}`)
        setEvaluationName(evalDetails.name)

        const data = await get<ResultsOverviewApiResponse>(`/evaluations/${evaluationId}/results`)
        setSummary(data.summary)
        setResults(data.results)
      } catch (err: any) {
        setError(err.message || 'Failed to load results')
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [evaluationId])

  const handleScriptClick = (scriptId: string) => {
    navigate(`/evaluation/${evaluationId}/results/${scriptId}`)
  }

  const getGradeStyle = (grade: string): string => {
    if (grade.startsWith('A')) return 'bg-green-100 text-green-700'
    if (grade.startsWith('B')) return 'bg-blue-100 text-blue-700'
    if (grade.startsWith('C')) return 'bg-yellow-100 text-yellow-700'
    return 'bg-red-100 text-red-700'
  }

  const reviewScripts = results.filter((r) => r.needs_human_review)
  const approvedScripts = results.filter((r) => !r.needs_human_review)

  const displayedResults =
    activeTab === 'review'
      ? reviewScripts
      : activeTab === 'approved'
      ? approvedScripts
      : results

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto py-12 flex justify-center items-center">
        <div className="flex flex-col items-center gap-4">
          <svg className="w-10 h-10 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-slate-600 font-medium">Loading evaluation results...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto py-12">
        <div className="bg-red-50 border-2 border-red-200 rounded-lg p-6 text-center">
          <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <h2 className="text-xl font-bold text-red-800 mb-2">Error Loading Results</h2>
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 mb-2">Results Overview</h1>
          <p className="text-slate-600">
            Evaluation: <span className="font-semibold text-slate-800">{evaluationName}</span>
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/evaluation/${evaluationId}/export`)}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-900 text-white px-4 py-2 rounded-lg font-semibold transition-colors shadow-sm text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export Results
          </button>
        </div>
      </div>

      {/* Stage 4 Human Review Alert Banner */}
      {reviewScripts.length > 0 && (
        <div className="mb-8 bg-amber-50 border-2 border-amber-300 rounded-xl p-5 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-amber-100 text-amber-800 rounded-lg shrink-0 mt-0.5">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-base font-bold text-amber-900">
                {reviewScripts.length} script(s) require educator verification (Stage 4 Triage)
              </h3>
              <p className="text-sm text-amber-800 mt-1">
                These papers have borderline scores within 2.5% of grade boundaries or contain ambiguous handwriting/diagram markings.
              </p>
              <div className="mt-3">
                <button
                  onClick={() => {
                    setActiveTab('review')
                    setSearchParams({ tab: 'review' })
                  }}
                  className="bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold px-4 py-1.5 rounded-md transition-colors"
                >
                  Filter Flagged Scripts ({reviewScripts.length})
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Summary Metrics */}
      <div className="grid md:grid-cols-4 gap-6 mb-8">
        {/* Total Scripts */}
        <div className="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm9.707 5.707a1 1 0 00-1.414-1.414L9 12.586l-1.293-1.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <p className="text-sm font-semibold text-slate-600 uppercase tracking-wider">Total Scripts</p>
          </div>
          <p className="text-4xl font-bold text-slate-800 mt-4">{summary.total_students}</p>
        </div>

        {/* Average Score */}
        <div className="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M5.5 16a3.5 3.5 0 01-.369-6.98 4 4 0 117.759-1.576 1.5 1.5 0 112.738-.088A2.999 2.999 0 0116 13h-1v-1a1 1 0 10-2 0v1h-1a1 1 0 10-2 0v-1a1 1 0 10-2 0v1H7.5A1.5 1.5 0 006 14.5V16h-.5z" />
              </svg>
            </div>
            <p className="text-sm font-semibold text-slate-600 uppercase tracking-wider">Average %</p>
          </div>
          <p className="text-4xl font-bold text-slate-800 mt-4">
            {summary.average_percentage}
            <span className="text-2xl text-slate-400 font-normal">%</span>
          </p>
        </div>

        {/* Highest Score */}
        <div className="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            </div>
            <p className="text-sm font-semibold text-slate-600 uppercase tracking-wider">Highest Marks</p>
          </div>
          <p className="text-4xl font-bold text-slate-800 mt-4">{summary.highest_score}</p>
        </div>

        {/* Lowest Score */}
        <div className="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clipRule="evenodd" />
              </svg>
            </div>
            <p className="text-sm font-semibold text-slate-600 uppercase tracking-wider">Lowest Marks</p>
          </div>
          <p className="text-4xl font-bold text-slate-800 mt-4">{summary.lowest_score}</p>
        </div>
      </div>

      {/* Results Table Section */}
      <div className="bg-white border-2 border-slate-200 rounded-lg overflow-hidden shadow-sm">
        {/* Table Header & Tabs */}
        <div className="p-6 border-b border-slate-200 flex flex-wrap justify-between items-center gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-800">Student Results</h2>
            <p className="text-sm text-slate-600 mt-0.5">Click on any row to view breakdown and educator review</p>
          </div>

          {/* Filter Tabs */}
          <div className="flex bg-slate-100 p-1 rounded-lg">
            <button
              onClick={() => {
                setActiveTab('all')
                setSearchParams({})
              }}
              className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all ${
                activeTab === 'all'
                  ? 'bg-white text-slate-800 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All ({results.length})
            </button>
            <button
              onClick={() => {
                setActiveTab('review')
                setSearchParams({ tab: 'review' })
              }}
              className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'review'
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'text-amber-700 hover:text-amber-900'
              }`}
            >
              Needs Review ({reviewScripts.length})
            </button>
            <button
              onClick={() => {
                setActiveTab('approved')
                setSearchParams({ tab: 'approved' })
              }}
              className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all ${
                activeTab === 'approved'
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Verified ({approvedScripts.length})
            </button>
          </div>
        </div>

        {displayedResults.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            No scripts found in this category.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left p-4 text-xs font-bold text-slate-600 uppercase tracking-wider">File / Student</th>
                  <th className="text-center p-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Marks</th>
                  <th className="text-center p-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Percentage</th>
                  <th className="text-center p-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Grade</th>
                  <th className="text-center p-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {displayedResults.map((result) => {
                  const gradeStyle = getGradeStyle(result.grade)
                  const isFlagged = result.needs_human_review

                  return (
                    <tr
                      key={result._id}
                      onClick={() => handleScriptClick(result._id)}
                      className="hover:bg-blue-50 cursor-pointer transition-colors duration-150 group"
                    >
                      <td className="p-4">
                        <div className="font-semibold text-slate-800 group-hover:text-blue-700 transition-colors">
                          {result.student_name}
                        </div>
                        <span className="text-slate-500 font-mono text-xs">{result.file_name}</span>
                        {isFlagged && result.review_reasons && result.review_reasons.length > 0 && (
                          <div className="text-[11px] text-amber-700 font-medium mt-1">
                            ↳ {result.review_reasons[0]}
                          </div>
                        )}
                      </td>
                      <td className="p-4 text-center">
                        <span className="font-bold text-slate-800">{result.total_score}</span>
                        <span className="text-slate-500 text-xs ml-1">/{result.max_score}</span>
                      </td>
                      <td className="p-4 text-center">
                        <div className="flex items-center justify-center gap-3">
                          <div className="w-20 bg-slate-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                result.percentage >= 80
                                  ? 'bg-green-500'
                                  : result.percentage >= 60
                                  ? 'bg-blue-500'
                                  : result.percentage >= 40
                                  ? 'bg-yellow-500'
                                  : 'bg-red-500'
                              }`}
                              style={{ width: `${result.percentage}%` }}
                            ></div>
                          </div>
                          <span className="text-sm font-bold text-slate-700 w-10 text-right">{result.percentage}%</span>
                        </div>
                      </td>
                      <td className="p-4 text-center">
                        <div className="relative inline-block">
                          <span
                            onMouseEnter={() => setHoveredResultId(result._id)}
                            onMouseLeave={() => setHoveredResultId(null)}
                            className={`inline-block px-3 py-1 rounded-md text-sm font-bold cursor-help ${gradeStyle}`}
                          >
                            {result.grade}
                          </span>
                          {hoveredResultId === result._id && (result.top_loss_component || result.feedback_summary || result.evaluation_method) && (
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-[250px] bg-white border border-slate-200 rounded-lg shadow-lg text-xs p-3 z-50 text-left">
                              {result.top_loss_component && (
                                <p className="font-semibold text-slate-800 mb-1">{result.top_loss_component}</p>
                              )}
                              {result.evaluation_method && (
                                <p className="text-slate-600 mb-1">
                                  {result.evaluation_method === 'fallback' ? '⚠️ Fallback-graded' : '✅ AI Model-graded'}
                                </p>
                              )}
                              {result.feedback_summary && (
                                <p className="text-slate-500 italic truncate">{result.feedback_summary.split('\n')[0]}</p>
                              )}
                              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-white z-10"></div>
                              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-200 mt-[1px]"></div>
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="p-4 text-center">
                        {result.status === 'failed' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800">
                            <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span> Failed
                          </span>
                        ) : isFlagged ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span> Needs Review
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                            ✓ Verified
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default ResultsOverview
