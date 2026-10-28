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
  run_id?: string
  log_folder?: string
  total_sheets: number
  message: string
}

interface PipelineStatusResponse {
  evaluation_id: string
  status: string
  pipeline_stage: string
  total_sheets: number
  completed_sheets: number
  failed_sheets?: number
  needs_review_count: number
  progress_percentage: number
  errors?: string[]
  latest_run_id?: string
  latest_log_dir?: string
}

interface ListSheetsResponse {
  success: boolean
  sheets: { id: string; status: string; needs_human_review?: boolean; error?: string }[]
}

export interface StreamEvent {
  id: string
  type: string
  level: 'info' | 'success' | 'warning' | 'error' | 'stage'
  message: string
  timestamp: string
  data?: Record<string, any>
}

// 5-Stage Offline Pipeline definition matching architecture
const OFFLINE_STAGES = [
  {
    id: 'stage0',
    name: 'Stage 0: Resolution & Crop Preprocessing',
    description: 'Bilinear normalization (1600x1200) and sliding-window visual block segmentation',
  },
  {
    id: 'stage1',
    name: 'Stage 1: Unified Multimodal Transcription',
    description: 'Qwen3-VL handwriting recognition to verbatim Markdown with inline LaTeX math',
  },
  {
    id: 'stage2',
    name: 'Stage 2: Hand-Drawn Diagram & Structure Perception',
    description: 'Dynamic graph topological description of user-sketched flowcharts and architecture diagrams',
  },
  {
    id: 'stage3',
    name: 'Stage 3: Rubric Alignment & Dynamic Assessment',
    description: 'Scoring against institutional marking scheme criteria with step-by-step rationale',
  },
  {
    id: 'stage4',
    name: 'Stage 4: Flagging & Educator Triage Queue',
    description: 'Automated triage routing borderline scores (<60%) and ambiguities to educator review',
  },
] as const

export default function ProcessEvaluation() {
  const { evaluationId } = useParams<{ evaluationId: string }>()
  const navigate = useNavigate()

  const [evaluationName, setEvaluationName] = useState('Loading...')
  const [totalScripts, setTotalScripts] = useState(0)
  const [evaluationStatus, setEvaluationStatus] = useState<EvaluationStatus>('not-started')
  const [needsReviewCount, setNeedsReviewCount] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [runFolder, setRunFolder] = useState<string | null>(null)

  // SSE Live Streaming State
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([])
  const [streamStatus, setStreamStatus] = useState<'idle' | 'connecting' | 'connected' | 'disconnected'>('idle')
  const [autoScroll, setAutoScroll] = useState(true)
  const [copied, setCopied] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const terminalEndRef = useRef<HTMLDivElement | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

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

  // Update a specific stage
  const updateStage = useCallback((stageIndex: number, updates: Partial<EvaluationStage>) => {
    setStages((prev) => {
      const copy = [...prev]
      copy[stageIndex] = { ...copy[stageIndex], ...updates }
      return copy
    })
  }, [])

  // Start Real-Time Server-Sent Events (SSE) Stream
  const startEventSource = useCallback(() => {
    if (!evaluationId) return
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    setStreamStatus('connecting')
    const sseUrl = `/api/evaluations/${evaluationId}/pipeline/stream`
    const es = new EventSource(sseUrl)
    eventSourceRef.current = es

    es.onopen = () => {
      setStreamStatus('connected')
    }

    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data)
        if (payload.type === 'connected') {
          setStreamStatus('connected')
          return
        }

        const newEvent: StreamEvent = {
          id: `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
          type: payload.type || 'info',
          level: payload.level || 'info',
          message: payload.message || '',
          timestamp: payload.timestamp || new Date().toLocaleTimeString(),
          data: payload.data,
        }

        setStreamEvents((prev) => [...prev, newEvent])

        // Live stage & status synchronization from SSE
        if (payload.type === 'pipeline_start') {
          setEvaluationStatus('processing')
          setError(null)
          if (payload.data?.log_folder) {
            setRunFolder(payload.data.log_folder)
          }
          updateStage(0, { status: 'in-progress', progress: 50 })
        } else if (payload.type === 'sheet_start') {
          updateStage(0, { status: 'completed', progress: 100 })
          updateStage(1, { status: 'in-progress', progress: 40 })
          updateStage(2, { status: 'in-progress', progress: 40 })
        } else if (payload.type === 'vlm_dispatch') {
          updateStage(1, { status: 'in-progress', progress: 85 })
          updateStage(2, { status: 'in-progress', progress: 80 })
        } else if (payload.type === 'vlm_complete') {
          updateStage(1, { status: 'completed', progress: 100 })
          updateStage(2, { status: 'completed', progress: 100 })
          updateStage(3, { status: 'in-progress', progress: 65 })
        } else if (payload.type === 'sheet_completed') {
          updateStage(3, { status: 'completed', progress: 100 })
          updateStage(4, { status: 'completed', progress: 100 })
          if (payload.data?.needs_review) {
            setNeedsReviewCount((c) => c + 1)
          }
        } else if (payload.type === 'sheet_error') {
          setError(payload.data?.error || payload.message)
          setStages((prev) => prev.map((st) => ({ ...st, status: 'error' })))
        } else if (payload.type === 'pipeline_done') {
          if (payload.data?.final_status === 'failed') {
            setEvaluationStatus('error')
            setStages((prev) => prev.map((st) => ({ ...st, status: 'error' })))
          } else {
            setEvaluationStatus('completed')
            setStages((prev) => prev.map((st) => ({ ...st, status: 'completed', progress: 100 })))
          }
          if (payload.data?.log_folder) {
            setRunFolder(payload.data.log_folder)
          }
        }
      } catch (err) {
        // Heartbeat or comment
      }
    }

    es.onerror = () => {
      setStreamStatus('disconnected')
    }
  }, [evaluationId, updateStage])

  // Poll database status as safety sync
  const startPollingPipeline = useCallback(() => {
    if (!evaluationId) return
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }

    pollingRef.current = setInterval(async () => {
      try {
        const [pipelineData, sheetsData] = await Promise.all([
          get<PipelineStatusResponse>(`/evaluations/${evaluationId}/pipeline/status`),
          get<ListSheetsResponse>(`/evaluations/${evaluationId}/sheets`),
        ])

        const total = pipelineData.total_sheets || sheetsData.sheets.length || 1
        const sheets = sheetsData.sheets
        setNeedsReviewCount(pipelineData.needs_review_count)
        if (pipelineData.latest_log_dir) {
          setRunFolder(pipelineData.latest_log_dir)
        }

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

        // Sync stage indicators
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

        // Capture backend errors
        if (pipelineData.errors && pipelineData.errors.length > 0) {
          setError(pipelineData.errors.join('\n'))
        }

        const failedCount = pipelineData.failed_sheets || sheets.filter((s) => s.status === 'failed').length

        if (pipelineData.status === 'failed' || (failedCount === total && total > 0)) {
          clearInterval(pollingRef.current!)
          pollingRef.current = null
          setEvaluationStatus('error')
          const errorMsg = pipelineData.errors?.length
            ? pipelineData.errors.join('\n')
            : 'Evaluation failed during model inference. Check backend and Ollama service.'
          setError(errorMsg)
          setStages((prev) => prev.map((st) => ({ ...st, status: 'error' })))
          return
        }

        // Check completion
        if (pipelineData.status === 'completed' || ((s3Done + failedCount) === total && total > 0)) {
          clearInterval(pollingRef.current!)
          pollingRef.current = null
          if (failedCount > 0 && s3Done === 0) {
            setEvaluationStatus('error')
            setStages((prev) => prev.map((st) => ({ ...st, status: 'error' })))
          } else {
            setEvaluationStatus('completed')
            setStages((prev) => prev.map((st) => ({ ...st, status: 'completed', progress: 100 })))
          }
        }
      } catch (err: any) {
        console.warn('Pipeline polling error:', err.message)
      }
    }, 6000)
  }, [evaluationId, updateStage])

  // Initial load & automatic SSE connection
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
        if (pipelineData.latest_log_dir) {
          setRunFolder(pipelineData.latest_log_dir)
        }

        if (pipelineData.status === 'completed') {
          setEvaluationStatus('completed')
          setStages((prev) => prev.map((st) => ({ ...st, status: 'completed', progress: 100 })))
        } else if (pipelineData.status === 'processing') {
          setEvaluationStatus('processing')
          startPollingPipeline()
          startEventSource()
        } else {
          setEvaluationStatus('not-started')
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load evaluation')
      }
    }
    load()
  }, [evaluationId, startPollingPipeline, startEventSource])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
      if (eventSourceRef.current) eventSourceRef.current.close()
    }
  }, [])

  // Auto-scroll terminal on new event
  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [streamEvents, autoScroll])

  // Start the full offline evaluation pipeline
  const handleStartEvaluation = async () => {
    setEvaluationStatus('processing')
    setError(null)
    setStreamEvents([])

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

    // Connect SSE immediately so user sees initial dispatch live
    startEventSource()

    try {
      const res = await post<PipelineStartResponse>(`/evaluations/${evaluationId}/pipeline/start`)
      if (res.log_folder) {
        setRunFolder(res.log_folder)
      }
      startPollingPipeline()
    } catch (err: any) {
      setEvaluationStatus('error')
      setError(`Failed to start pipeline: ${err.message}`)
    }
  }

  // Copy logs helper
  const handleCopyLogs = () => {
    const text = streamEvents.map((e) => `[${e.timestamp}] [${e.level.toUpperCase()}] ${e.message}`).join('\n')
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
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
    return (
      <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${styles[status]}`}>
        {labels[status]}
      </span>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate('/evaluations')}
          className="text-sm text-slate-600 hover:text-slate-900 mb-4 inline-flex items-center gap-1"
        >
          ← Back to Evaluations
        </button>
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Process Evaluation (Offline Pipeline)</h1>
        <p className="text-slate-600">
          Run the 5-stage CPU pipeline for: <span className="font-semibold text-slate-800">{evaluationName}</span>
        </p>
      </div>

      {/* Evaluation Info Card */}
      <div className="bg-white border-2 border-slate-200 rounded-lg p-6 mb-8 shadow-sm">
        <div className="grid md:grid-cols-4 gap-6 items-center">
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
          <div>
            <p className="text-sm text-slate-500 mb-1">Run Logs Folder</p>
            <div className="flex items-center gap-1.5">
              <span className="text-xs">📁</span>
              <p
                className="text-xs font-mono bg-slate-100 px-2 py-1.5 rounded text-slate-700 truncate max-w-full"
                title={runFolder || 'Logs created on execution'}
              >
                {runFolder ? runFolder.split(/[\\/]/).slice(-3).join('/') : 'logs/[eval_id]/run_[ts]'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-300 rounded-lg p-5 mb-8 shadow-sm">
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 text-red-600 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h3 className="text-sm font-bold text-red-900 mb-1">Pipeline Execution Error</h3>
              <p className="text-sm text-red-800 whitespace-pre-line leading-relaxed">{error}</p>
            </div>
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
              <button
                onClick={() => navigate(`/evaluations/${evaluationId}/results`)}
                className="px-5 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-lg shadow transition-colors"
              >
                View Results →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Real-Time SSE Pipeline Stream Console */}
      <div className="bg-slate-900 border-2 border-slate-700/80 rounded-xl mb-8 overflow-hidden shadow-2xl">
        {/* Console Header */}
        <div className="bg-slate-950 px-4 py-3 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-3">
            {/* macOS window control dots */}
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/80 border border-red-600"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500/80 border border-yellow-600"></div>
              <div className="w-3 h-3 rounded-full bg-green-500/80 border border-green-600"></div>
            </div>
            <span className="text-xs font-mono font-medium text-slate-300 flex items-center gap-2">
              <span>pipeline_stream.sh</span>
              <span className="text-slate-600">|</span>
              <span className="text-slate-400">SSE Real-Time Stream</span>
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Live Indicator */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono bg-slate-900 border border-slate-800">
              {streamStatus === 'connected' ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="text-emerald-400 font-semibold tracking-wider text-[10px]">LIVE STREAMING</span>
                </>
              ) : streamStatus === 'connecting' ? (
                <>
                  <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse"></span>
                  <span className="text-amber-400 text-[10px]">CONNECTING...</span>
                </>
              ) : (
                <>
                  <span className="h-2 w-2 rounded-full bg-slate-500"></span>
                  <span className="text-slate-400 text-[10px]">IDLE</span>
                </>
              )}
            </div>

            {/* Auto-scroll toggle */}
            <button
              type="button"
              onClick={() => setAutoScroll(!autoScroll)}
              className={`text-xs px-2.5 py-1 rounded border font-mono transition-colors ${
                autoScroll
                  ? 'bg-blue-600/30 text-blue-300 border-blue-500/40 hover:bg-blue-600/40'
                  : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
              }`}
            >
              Auto-scroll: {autoScroll ? 'ON' : 'OFF'}
            </button>

            {/* Copy Logs */}
            <button
              type="button"
              onClick={handleCopyLogs}
              className="text-xs px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700 font-mono transition-colors"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>

            {/* Clear console */}
            <button
              type="button"
              onClick={() => setStreamEvents([])}
              className="text-xs px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700 font-mono transition-colors"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Console Body */}
        <div className="bg-slate-950 p-4 font-mono text-xs text-slate-200 h-80 overflow-y-auto space-y-1.5 select-text">
          {streamEvents.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-2">
              <svg className="w-8 h-8 opacity-40 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <p className="text-center">
                Waiting for backend pipeline events...<br />
                Click <span className="text-blue-400 font-semibold">Start Pipeline</span> to stream live backend execution.
              </p>
            </div>
          ) : (
            streamEvents.map((evt) => (
              <div key={evt.id} className="flex items-start gap-2.5 leading-relaxed py-0.5 hover:bg-slate-900/40 px-1.5 rounded transition-colors">
                <span className="text-slate-500 shrink-0 select-none">[{evt.timestamp}]</span>
                <span
                  className={`shrink-0 font-semibold text-[10px] uppercase px-1.5 py-0.5 rounded border select-none ${
                    evt.level === 'success'
                      ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/40'
                      : evt.level === 'error'
                      ? 'bg-rose-950/60 text-rose-400 border-rose-800/40 font-bold'
                      : evt.level === 'warning'
                      ? 'bg-amber-950/60 text-amber-400 border-amber-800/40'
                      : evt.level === 'stage'
                      ? 'bg-purple-950/60 text-purple-400 border-purple-800/40'
                      : 'bg-cyan-950/60 text-cyan-400 border-cyan-800/40'
                  }`}
                >
                  {evt.level === 'success' ? 'OK' : evt.level.toUpperCase()}
                </span>
                <span
                  className={`flex-1 break-words ${
                    evt.level === 'error'
                      ? 'text-rose-300 font-semibold'
                      : evt.level === 'success'
                      ? 'text-emerald-200'
                      : evt.level === 'warning'
                      ? 'text-amber-200'
                      : evt.level === 'stage'
                      ? 'text-purple-200 font-medium'
                      : 'text-slate-300'
                  }`}
                >
                  {evt.message}
                </span>

                {/* Optional score badge */}
                {evt.data?.score !== undefined && (
                  <span className="shrink-0 bg-emerald-900/40 border border-emerald-700/50 text-emerald-300 px-2 py-0.5 rounded text-[11px] font-bold">
                    Score: {evt.data.score}/{evt.data.max_score} ({evt.data.grade})
                  </span>
                )}
              </div>
            ))
          )}
          <div ref={terminalEndRef} />
        </div>

        {/* Console Footer */}
        <div className="bg-slate-900 px-4 py-2 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <div className="flex items-center gap-4">
            <span>Total Events: <strong className="text-slate-200">{streamEvents.length}</strong></span>
            {runFolder && (
              <span className="truncate max-w-md text-slate-500">
                Run Folder: <strong className="text-slate-400 font-mono">{runFolder.split(/[\\/]/).slice(-3).join('/')}</strong>
              </span>
            )}
          </div>
          <span className="text-slate-500 text-[10px]">Real-Time SSE Engine</span>
        </div>
      </div>

      {/* 5-Stage Pipeline Progress Cards */}
      <div className="space-y-4">
        {stages.map((stage, idx) => (
          <div
            key={stage.id}
            className={`bg-white border-2 rounded-lg p-6 transition-all duration-200 ${
              stage.status === 'in-progress'
                ? 'border-blue-400 shadow-md ring-1 ring-blue-400'
                : stage.status === 'completed'
                ? 'border-green-200 bg-green-50/20'
                : stage.status === 'error'
                ? 'border-red-300 bg-red-50/20'
                : 'border-slate-200'
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold bg-slate-100 text-slate-700 border border-slate-300">
                  {idx}
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-800">{stage.name}</h3>
                  <p className="text-xs text-slate-500 mt-0.5">{stage.description}</p>
                </div>
              </div>
              {getStatusBadge(stage.status)}
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <div
                className={`h-2.5 rounded-full transition-all duration-500 ${
                  stage.status === 'completed'
                    ? 'bg-green-500'
                    : stage.status === 'in-progress'
                    ? 'bg-blue-600'
                    : stage.status === 'error'
                    ? 'bg-red-500'
                    : 'bg-slate-300'
                }`}
                style={{ width: `${stage.progress}%` }}
              ></div>
            </div>
            <div className="flex justify-between items-center mt-1.5 text-xs text-slate-400">
              <span>{stage.status === 'in-progress' ? 'Processing...' : stage.status === 'completed' ? 'Done' : 'Waiting'}</span>
              <span>{stage.progress}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
