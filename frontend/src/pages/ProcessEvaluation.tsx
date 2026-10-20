import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import type { StageStatus, EvaluationStage, EvaluationStatus } from '@/types'
import { get, post } from '@/api/client'

// Backend response types
interface EvaluationApiResponse {
  id: string
  name: string
  subject: string
  max_marks: number
  answer_type: string
  status: string
  pipeline_stage?: string
}

interface PipelineStartResponse {
  success: boolean
  evaluation_id: string
  total_sheets: number
  message: string
}

interface PipelineStatusResponse {
  evaluation_id: string
  status: string
  pipeline_stage: string
  total_sheets: number
  completed_sheets: number
  needs_review_count: number
  progress_percentage: number
}

interface ListSheetsResponse {
  success: boolean
  sheets: { id: string; status: string; needs_human_review?: boolean }[]
}

// Unified Multimodal VLM Pipeline Configuration (Qwen3-VL:8b)
const OFFLINE_STAGES = [
  {
    id: 'stage0',
    name: 'Stage 0: Ingestion & Resolution Normalization',
    description: 'Contrast conditioning & 1280px scaling optimized for local vision-encoder throughput',
  },
  {
    id: 'stage1',
    name: 'Stage 1: Unified Multimodal Transcription',
    description: 'Local Qwen3-VL 8B transcribing handwritten text, LaTeX math formulas & matrix notation',
  },
  {
    id: 'stage2',
    name: 'Stage 2: Structural Diagram & Graph Parsing',
    description: 'Translating hand-drawn graphs, trees, and state matrices into structural representations',
  },
  {
    id: 'stage3',
    name: 'Stage 3: Rubric Assessment & Grading',
    description: 'Evaluating student steps against institutional rubric with automated mark derivation',
  },
  {
    id: 'stage4',
    name: 'Stage 4: Flagging & Educator Triage Queue',
    description: 'Automated triage routing borderline scores (<60%) and ambiguities to educator review',
  },
] as const

function ProcessEvaluation() {
  const { evaluationId } = useParams<{ evaluationId: string }>()
  const navigate = useNavigate()

  const [evaluationName, setEvaluationName] = useState('Loading...')
  const [totalScripts, setTotalScripts] = useState(0)
  const [evaluationStatus, setEvaluationStatus] = useState<EvaluationStatus>('not-started')
  const [needsReviewCount, setNeedsReviewCount] = useState(0)
  const [error, setError] = useState<string | null>(null)

  // Pipeline stages
  const [stages, setStages] = useState<EvaluationStage[]>(
    OFFLINE_STAGES.map((cfg) => ({
      id: cfg.id,
      name: cfg.name,
      description: cfg.description,
      status: 'pending' as StageStatus,
      progress: 0,
    }))
  )

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Update a specific stage
  const updateStage = useCallback((stageIndex: number, updates: Partial<EvaluationStage>) => {
    setStages((prev) => {
      const copy = [...prev]
      copy[stageIndex] = { ...copy[stageIndex], ...updates }
      return copy
    })
  }, [])

  // Poll the unified offline pipeline status
  const startPollingPipeline = useCallback(() => {
    if (!evaluationId) return
    if (pollingRef.current) clearInterval(pollingRef.current)

    pollingRef.current = setInterval(async () => {
      try {
        const [pipelineData, sheetsData] = await Promise.all([
          get<PipelineStatusResponse>(`/evaluations/${evaluationId}/pipeline/status`),
          get<ListSheetsResponse>(`/evaluations/${evaluationId}/sheets`),
        ])

        const total = pipelineData.total_sheets || sheetsData.sheets.length || 1
        const sheets = sheetsData.sheets
        setNeedsReviewCount(pipelineData.needs_review_count)

        // Stage 0: Preprocessing & Crop
        const s0Done = sheets.filter((s) =>
          ['preprocessing-completed', 'transcribing-pending', 'transcribing-processing', 'grading-pending', 'grading-processing', 'evaluation-completed', 'review-needed'].includes(s.status)
        ).length
        const s0Pct = Math.round((s0Done / total) * 100)

        // Stage 1 & 2: Unified Multimodal Transcription & Diagrams
        const isVlmRunning = sheets.some((s) => ['transcribing-processing'].includes(s.status))
        const s1Done = sheets.filter((s) =>
          ['grading-pending', 'grading-processing', 'evaluation-completed', 'review-needed'].includes(s.status)
        ).length
        const s1Pct = Math.round((s1Done / total) * 100)

        // Stage 3 & 4: Rubric Assessment & Triage
        const s3Done = sheets.filter((s) =>
          ['evaluation-completed', 'review-needed'].includes(s.status)
        ).length
        const s3Pct = Math.round((s3Done / total) * 100)
        const s4Pct = s3Pct

        // Update stages state
        updateStage(0, {
          progress: s0Pct,
          status: s0Pct === 100 ? 'completed' : s0Pct > 0 ? 'in-progress' : 'pending',
        })
        updateStage(1, {
          progress: s1Pct === 100 ? 100 : (isVlmRunning ? Math.max(65, s1Pct) : s1Pct),
          status: s1Pct === 100 ? 'completed' : (isVlmRunning || s1Pct > 0) ? 'in-progress' : 'pending',
        })
        updateStage(2, {
          progress: s1Pct === 100 ? 100 : (isVlmRunning ? Math.max(50, s1Pct) : s1Pct),
          status: s1Pct === 100 ? 'completed' : (isVlmRunning || s1Pct > 0) ? 'in-progress' : 'pending',
        })
        updateStage(3, {
          progress: s3Pct,
          status: s3Pct === 100 ? 'completed' : s3Pct > 0 ? 'in-progress' : 'pending',
        })
        updateStage(4, {
          progress: s4Pct,
          status: s4Pct === 100 ? 'completed' : s4Pct > 0 ? 'in-progress' : 'pending',
        })

        // Check if finished
        if (pipelineData.status === 'completed' || (s3Done === total && total > 0)) {
          clearInterval(pollingRef.current!)
          pollingRef.current = null
          setEvaluationStatus('completed')
          setStages((prev) => prev.map((st) => ({ ...st, status: 'completed', progress: 100 })))
        }
      } catch (err: any) {
        console.warn('Pipeline polling error:', err.message)
      }
    }, 1500)
  }, [evaluationId, updateStage])

  // Initial load
  useEffect(() => {
    if (!evaluationId) return
    const load = async () => {
      try {
        const eval_ = await get<EvaluationApiResponse>(`/evaluations/${evaluationId}`)
        setEvaluationName(eval_.name)

        const sheets = await get<ListSheetsResponse>(`/evaluations/${evaluationId}/sheets`)
        setTotalScripts(sheets.sheets.length)

        if (sheets.sheets.length === 0) {
          setError('No sheets uploaded yet. Go back and upload answer sheets first.')
          return
        }

        const pipelineData = await get<PipelineStatusResponse>(`/evaluations/${evaluationId}/pipeline/status`)
        setNeedsReviewCount(pipelineData.needs_review_count)

        if (pipelineData.status === 'completed') {
          setEvaluationStatus('completed')
          setStages((prev) => prev.map((st) => ({ ...st, status: 'completed', progress: 100 })))
        } else if (pipelineData.status === 'processing') {
          setEvaluationStatus('processing')
          startPollingPipeline()
        } else {
          setEvaluationStatus('not-started')
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load evaluation')
      }
    }
    load()
  }, [evaluationId, startPollingPipeline])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [])

  // Start the full offline evaluation pipeline
  const handleStartEvaluation = async () => {
    setEvaluationStatus('processing')
    setError(null)

    // Reset stages
    setStages(
      OFFLINE_STAGES.map((cfg) => ({
        id: cfg.id,
        name: cfg.name,
        description: cfg.description,
        status: 'pending' as StageStatus,
        progress: 0,
      }))
    )

    try {
      await post<PipelineStartResponse>(`/evaluations/${evaluationId}/pipeline/start`)
      startPollingPipeline()
    } catch (err: any) {
      setEvaluationStatus('error')
      setError(`Failed to start pipeline: ${err.message}`)
    }
  }

  // Get status badge styling
  const getStatusBadge = (status: StageStatus) => {
    const styles = {
      pending: 'bg-slate-100 text-slate-600',
      'in-progress': 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700',
      error: 'bg-red-100 text-red-700',
    }
    const labels = {
      pending: 'Pending',
      'in-progress': 'In Progress',
      completed: 'Completed',
      error: 'Error',
    }
    return { style: styles[status], label: labels[status] }
  }

  // Get stage icon
  const getStageIcon = (stage: EvaluationStage) => {
    if (stage.status === 'completed') {
      return (
        <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
      )
    }
    if (stage.status === 'in-progress') {
      return (
        <svg className="w-8 h-8 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      )
    }
    if (stage.status === 'error') {
      return (
        <svg className="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
      )
    }
    return (
      <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Process Evaluation (Offline Pipeline)</h1>
        <p className="text-slate-600">
          Run the 5-stage CPU pipeline for: <span className="font-semibold text-slate-800">{evaluationName}</span>
        </p>
      </div>

      {/* Evaluation Info Card */}
      <div className="bg-white border-2 border-slate-200 rounded-lg p-6 mb-8">
        <div className="grid md:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-slate-500 mb-1">Evaluation Name</p>
            <p className="text-lg font-semibold text-slate-800">{evaluationName}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500 mb-1">Total Scripts</p>
            <p className="text-lg font-semibold text-slate-800">{totalScripts} answer sheets</p>
          </div>
          <div>
            <p className="text-sm text-slate-500 mb-1">Mode</p>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span> 100% Offline (Local CPU)
            </span>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-red-600 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <p className="text-sm text-red-800">{error}</p>
          </div>
        </div>
      )}

      {/* Control Panel */}
      <div className="bg-white border-2 border-slate-200 rounded-lg p-6 mb-8 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-800 mb-1">5-Stage Evaluation Pipeline</h2>
            <p className="text-sm text-slate-600">
              {evaluationStatus === 'not-started' && 'Ready to start offline batch evaluation'}
              {evaluationStatus === 'processing' && 'Processing batch across CPU worker queue...'}
              {evaluationStatus === 'completed' && 'Evaluation completed successfully!'}
              {evaluationStatus === 'error' && 'An error occurred during processing'}
            </p>
          </div>

          <button
            onClick={handleStartEvaluation}
            disabled={evaluationStatus === 'completed' || evaluationStatus === 'processing' || totalScripts === 0}
            className={`px-8 py-3 rounded-lg font-semibold transition-all duration-200 ${
              evaluationStatus === 'completed' || evaluationStatus === 'processing' || totalScripts === 0
                ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg'
            }`}
          >
            {evaluationStatus === 'processing'
              ? 'Processing...'
              : evaluationStatus === 'completed'
              ? 'Completed ✓'
              : evaluationStatus === 'error'
              ? 'Retry Pipeline'
              : 'Start Pipeline'}
          </button>
        </div>

        {evaluationStatus === 'completed' && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-green-600 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-sm font-semibold text-green-800">Batch evaluation complete!</p>
                  {needsReviewCount > 0 ? (
                    <p className="text-xs text-amber-700 font-medium mt-0.5">
                      ⚠️ {needsReviewCount} script(s) flagged for human verification (borderline score or handwriting uncertainty).
                    </p>
                  ) : (
                    <p className="text-xs text-green-700">All scripts graded with high confidence.</p>
                  )}
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => navigate(`/evaluation/${evaluationId}/results`)}
                  className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-5 rounded-lg transition-colors text-sm shadow-sm"
                >
                  View Results Overview →
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Progress Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-bold text-slate-800 mb-4">Pipeline Execution Stages</h3>

        {stages.map((stage, index) => {
          const statusBadge = getStatusBadge(stage.status)
          const isLastStage = index === stages.length - 1

          return (
            <div key={stage.id}>
              <div className="bg-white border-2 border-slate-200 rounded-lg p-6 shadow-sm">
                {/* Stage Header */}
                <div className="flex items-start gap-4 mb-4">
                  <div className="shrink-0">{getStageIcon(stage)}</div>

                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-lg font-bold text-slate-800">{stage.name}</h4>
                      <span className={`px-3 py-1 text-xs font-semibold rounded-full ${statusBadge.style}`}>
                        {statusBadge.label}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600">{stage.description}</p>
                  </div>
                </div>

                {/* Progress Bar */}
                {(stage.status === 'in-progress' || stage.status === 'completed') && (
                  <div className="mt-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-slate-600">Progress</span>
                      <span className="text-xs font-semibold text-slate-600">{stage.progress}%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-300 ${
                          stage.status === 'completed' ? 'bg-green-600' : 'bg-blue-600'
                        }`}
                        style={{ width: `${stage.progress}%` }}
                      ></div>
                    </div>
                  </div>
                )}
              </div>

              {/* Connector Line */}
              {!isLastStage && (
                <div className="flex justify-center py-2">
                  <div className={`w-0.5 h-8 ${stage.status === 'completed' ? 'bg-green-400' : 'bg-slate-300'}`}></div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Info Box */}
      {evaluationStatus === 'not-started' && totalScripts > 0 && (
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex gap-3">
            <svg className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <div className="text-sm text-blue-800">
              <p className="font-semibold mb-1">Optimized CPU Evaluation</p>
              <p>
                The evaluation runs entirely offline using a 5-stage pipeline with KV-cache reuse across questions. All processing happens in a background worker queue, so you can safely leave or reload this page.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProcessEvaluation
