import { Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import type { Evaluation } from '@/types'
import { get, del } from '@/api/client'

// Backend response shape from GET /api/evaluations
interface EvaluationApiItem {
  id: string
  name: string
  subject: string
  max_marks: number
  answer_type: string
  status: string
}

interface EvaluationListApiResponse {
  success: boolean
  evaluations: EvaluationApiItem[]
}

/** Map backend snake_case response to frontend camelCase Evaluation type */
function toEvaluation(item: EvaluationApiItem): Evaluation {
  return {
    id: item.id,
    name: item.name,
    courseSubject: item.subject,
    maximumMarks: item.max_marks,
    answerType: item.answer_type as 'printed' | 'handwritten',
    createdAt: new Date().toISOString(), // backend doesn't return created_at in list response
    status: item.status as Evaluation['status'],
    totalSheets: 0,
  }
}

function Home() {
  const [recentEvaluations, setRecentEvaluations] = useState<Evaluation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch real evaluations from the backend
  const fetchEvaluations = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await get<EvaluationListApiResponse>('/evaluations')
      setRecentEvaluations(data.evaluations.map(toEvaluation))
    } catch (err: any) {
      setError(err.message || 'Failed to load evaluations')
      console.error('Failed to fetch evaluations:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchEvaluations()
  }, [])

  // Delete evaluation handler
  const handleDelete = async (evaluationId: string, e: React.MouseEvent) => {
    e.preventDefault() // prevent Link navigation
    e.stopPropagation()
    if (!window.confirm('Are you sure you want to delete this evaluation? This cannot be undone.')) return

    try {
      await del(`/evaluations/${evaluationId}`)
      setRecentEvaluations(prev => prev.filter(ev => ev.id !== evaluationId))
    } catch (err: any) {
      alert('Failed to delete: ' + (err.message || 'Unknown error'))
    }
  }

  // Helper function to get status badge styling
  const getStatusBadge = (status: Evaluation['status']) => {
    const styles = {
      draft: 'bg-slate-100 text-slate-700',
      'in-progress': 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700',
    }
    const labels = {
      draft: 'Draft',
      'in-progress': 'In Progress',
      completed: 'Completed',
    }
    return { style: styles[status] || styles.draft, label: labels[status] || status }
  }

  return (
    <div className="max-w-6xl mx-auto py-12">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-bold text-slate-800 mb-4">
          Sustainable AI Assessment Platform
        </h1>
        <p className="text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
          An offline, privacy-preserving platform for AI-powered evaluation of student assessments.
          Process answer sheets locally with complete data security and transparency.
        </p>
      </div>

      {/* Create New Evaluation Button */}
      <div className="mb-12">
        <Link
          to="/evaluation/new"
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-8 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Create New Evaluation
        </Link>
      </div>

      {/* Recent Evaluations Section */}
      <div className="mb-12">
        <h2 className="text-2xl font-bold text-slate-800 mb-6">Recent Evaluations</h2>

        {/* Error state */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <p className="text-sm text-red-800">{error}</p>
              <button onClick={fetchEvaluations} className="ml-auto text-sm font-semibold text-red-700 hover:text-red-800">Retry</button>
            </div>
          </div>
        )}

        {isLoading ? (
          // Loading skeleton
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white border-2 border-slate-200 rounded-lg p-6 animate-pulse">
                <div className="h-6 bg-slate-200 rounded w-3/4 mb-4"></div>
                <div className="h-4 bg-slate-200 rounded w-1/2 mb-2"></div>
                <div className="h-4 bg-slate-200 rounded w-2/3"></div>
              </div>
            ))}
          </div>
        ) : recentEvaluations.length === 0 && !error ? (
          // Empty state
          <div className="bg-slate-50 border-2 border-dashed border-slate-300 rounded-lg p-12 text-center">
            <svg className="w-16 h-16 text-slate-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="text-xl font-semibold text-slate-700 mb-2">No evaluations yet</h3>
            <p className="text-slate-600 mb-4">Get started by creating your first evaluation</p>
            <Link
              to="/evaluation/new"
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg transition-colors duration-200"
            >
              Create Evaluation
            </Link>
          </div>
        ) : (
          // Evaluations grid
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {recentEvaluations.map((evaluation) => {
              const statusBadge = getStatusBadge(evaluation.status)

              return (
                <Link
                  key={evaluation.id}
                  to={`/evaluation/${evaluation.id}/process`}
                  className="bg-white border-2 border-slate-200 rounded-lg p-6 hover:border-blue-400 hover:shadow-lg transition-all duration-200 group relative"
                >
                  {/* Delete button */}
                  <button
                    onClick={(e) => handleDelete(evaluation.id, e)}
                    className="absolute top-3 right-3 text-slate-400 hover:text-red-600 hover:bg-red-50 p-1.5 rounded transition-colors opacity-0 group-hover:opacity-100"
                    title="Delete evaluation"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>

                  {/* Header with status badge */}
                  <div className="flex items-start justify-between mb-4 pr-6">
                    <h3 className="text-lg font-bold text-slate-800 group-hover:text-blue-600 transition-colors line-clamp-2">
                      {evaluation.name}
                    </h3>
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full shrink-0 ml-2 ${statusBadge.style}`}>
                      {statusBadge.label}
                    </span>
                  </div>

                  {/* Evaluation details */}
                  <div className="space-y-2 text-sm text-slate-600">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-slate-400" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10.394 2.08a1 1 0 00-.788 0l-7 3a1 1 0 000 1.84L5.25 8.051a.999.999 0 01.356-.257l4-1.714a1 1 0 11.788 1.838L7.667 9.088l1.94.831a1 1 0 00.787 0l7-3a1 1 0 000-1.838l-7-3zM3.31 9.397L5 10.12v4.102a8.969 8.969 0 00-1.05-.174 1 1 0 01-.89-.89 11.115 11.115 0 01.25-3.762zM9.3 16.573A9.026 9.026 0 007 14.935v-3.957l1.818.78a3 3 0 002.364 0l5.508-2.361a11.026 11.026 0 01.25 3.762 1 1 0 01-.89.89 8.968 8.968 0 00-5.35 2.524 1 1 0 01-1.4 0zM6 18a1 1 0 001-1v-2.065a8.935 8.935 0 00-2-.712V17a1 1 0 001 1z" />
                      </svg>
                      <span>{evaluation.courseSubject}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-slate-400" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                        <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                      </svg>
                      <span>{evaluation.maximumMarks} marks • {evaluation.answerType}</span>
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>

      {/* Features Section */}
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-8">
        <h3 className="text-xl font-bold text-slate-800 mb-4 text-center">Platform Features</h3>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-3xl mb-2">🔒</div>
            <h4 className="font-semibold text-slate-700 mb-1">Privacy First</h4>
            <p className="text-sm text-slate-600">All processing happens locally on your device</p>
          </div>
          <div className="text-center">
            <div className="text-3xl mb-2">⚡</div>
            <h4 className="font-semibold text-slate-700 mb-1">Unified Multimodal VLM</h4>
            <p className="text-sm text-slate-600">Local Qwen3-VL (8B) extracting handwritten text, LaTeX math, & diagrams</p>
          </div>
          <div className="text-center">
            <div className="text-3xl mb-2">🎯</div>
            <h4 className="font-semibold text-slate-700 mb-1">Rubric-Based Evaluation</h4>
            <p className="text-sm text-slate-600">Institutional rubric criteria assessment with Stage 4 human review</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home
