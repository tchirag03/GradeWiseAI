import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { get, post } from '@/api/client'

// Backend API response types
interface OcrResult {
  sheet_id: string
  status: string
  result?: {
    extracted_text: string
    confidence: number
  }
}

interface ComponentScore {
  component: string
  marks_awarded: number
  max_marks: number
  feedback?: string
  model_answer?: string
}

interface QuestionScore {
  question_number: number
  question_text: string
  component_scores?: ComponentScore[]
  total_marks: number
  max_marks: number
  feedback: string
  grade_context?: string
  evaluation_method?: string
}

interface ScriptCrop {
  crop_id: string
  crop_type: string
  crop_path: string
  transcription?: string
  diagram_description?: string
}

interface ScriptResultDetails {
  success: boolean
  sheet_id: string
  student: {
    name: string
    file_name: string
  }
  needs_human_review?: boolean
  review_reasons?: string[]
  diagram_description?: string
  crops?: ScriptCrop[]
  evaluation?: {
    questions: QuestionScore[]
    total_score: number
    max_score: number
    percentage: number
    grade: string
  }
  message?: string
  rubric_file_name?: string
  rubric_components?: { name: string; marks: number; model_answer?: string; mark_bands?: string }[]
  grade_boundaries?: { grade: string; min_percentage: number }[]
  error?: string
  status?: string
}

function ScriptDetails() {
  const { evaluationId, scriptId } = useParams<{ evaluationId: string; scriptId: string }>()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [ocrText, setOcrText] = useState<string>('')
  const [details, setDetails] = useState<ScriptResultDetails | null>(null)

  // Review override state
  const [overrideScore, setOverrideScore] = useState<string>('')
  const [reviewNotes, setReviewNotes] = useState<string>('')
  const [isSavingReview, setIsSavingReview] = useState<boolean>(false)
  const [reviewSuccessMsg, setReviewSuccessMsg] = useState<string | null>(null)

  // Explainability states
  const [expandedSideBySide, setExpandedSideBySide] = useState<number | null>(null)

  useEffect(() => {
    if (!evaluationId || !scriptId) return

    const loadData = async () => {
      setIsLoading(true)
      try {
        const [ocrRes, detailsRes] = await Promise.all([
          get<OcrResult>(`/evaluations/${evaluationId}/ocr/result/${scriptId}`),
          get<ScriptResultDetails>(`/evaluations/${evaluationId}/results/${scriptId}`),
        ])

        if (ocrRes.result?.extracted_text) {
          setOcrText(ocrRes.result.extracted_text)
        } else {
          setOcrText('Text transcription not yet available.')
        }

        setDetails(detailsRes)
        if (detailsRes.evaluation) {
          setOverrideScore(String(detailsRes.evaluation.total_score))
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load script details')
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [evaluationId, scriptId])

  const getCategoryBadge = (pct: number) => {
    if (pct >= 80) return 'bg-green-100 text-green-700 border-green-200'
    if (pct >= 60) return 'bg-blue-100 text-blue-700 border-blue-200'
    if (pct >= 40) return 'bg-yellow-100 text-yellow-700 border-yellow-200'
    return 'bg-red-100 text-red-700 border-red-200'
  }

  const getProgressColor = (pct: number) => {
    if (pct >= 80) return 'bg-green-600'
    if (pct >= 60) return 'bg-blue-600'
    if (pct >= 40) return 'bg-yellow-600'
    return 'bg-red-600'
  }

  const handleBackToResults = () => {
    navigate(`/evaluation/${evaluationId}/results`)
  }

  // Handle Stage 4 Human Review Resolution
  const handleResolveReview = async () => {
    if (!evaluationId || !scriptId) return
    setIsSavingReview(true)
    setReviewSuccessMsg(null)

    try {
      await post(`/evaluations/${evaluationId}/review_queue/${scriptId}/resolve`, {
        approved: true,
        override_score: overrideScore ? parseFloat(overrideScore) : undefined,
        notes: reviewNotes || 'Approved by educator.',
      })

      setReviewSuccessMsg('Review resolved! Score updated and verification confirmed.')

      // Update local state
      if (details && details.evaluation) {
        const updatedTotal = overrideScore ? parseFloat(overrideScore) : details.evaluation.total_score
        const updatedPct = Math.round((updatedTotal / details.evaluation.max_score) * 100)
        setDetails({
          ...details,
          needs_human_review: false,
          evaluation: {
            ...details.evaluation,
            total_score: updatedTotal,
            percentage: updatedPct,
          },
        })
      }
    } catch (err: any) {
      alert(`Failed to save review: ${err.message}`)
    } finally {
      setIsSavingReview(false)
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto py-12 flex justify-center items-center">
        <div className="flex flex-col items-center gap-4">
          <svg className="w-10 h-10 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-slate-600 font-medium">Loading script analysis...</p>
        </div>
      </div>
    )
  }

  if (error || !details) {
    return (
      <div className="max-w-7xl mx-auto py-12">
        <div className="bg-red-50 border-2 border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-xl font-bold text-red-800 mb-2">Error Loading Script</h2>
          <p className="text-red-600">{error || 'Unknown error'}</p>
          <button
            onClick={handleBackToResults}
            className="mt-6 bg-slate-800 hover:bg-slate-900 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
          >
            Back to Results
          </button>
        </div>
      </div>
    )
  }

  const evalData = details.evaluation
  const figureCrops = (details.crops || []).filter((c) => c.crop_type === 'figure' && c.diagram_description)

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={handleBackToResults}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-semibold mb-4 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Results
        </button>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-800 mb-2">Script Details</h1>
            <div className="flex flex-wrap items-center gap-4 text-slate-600">
              <span>
                <span className="font-semibold text-slate-800">Student:</span> {details.student.name}
              </span>
              <span className="text-slate-300">•</span>
              <span className="font-mono text-sm">
                <span className="font-semibold font-sans text-slate-800">File:</span> {details.student.file_name}
              </span>
            </div>
          </div>

          {/* Score Badge */}
          {evalData && (
            <div className={`text-white rounded-lg p-4 text-center min-w-[130px] shadow-sm ${getProgressColor(evalData.percentage)}`}>
              <p className="text-sm font-semibold mb-1 opacity-90">Total Score</p>
              <p className="text-4xl font-bold tracking-tight">{evalData.total_score}</p>
              <p className="text-xs mt-1 opacity-80 border-t border-white/20 pt-1">out of {evalData.max_score}</p>
              <div className="mt-2 bg-black/20 rounded px-2 py-1 flex items-center justify-between text-xs font-bold">
                <span>{evalData.percentage}%</span>
                <span>Grade {evalData.grade}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Execution Error Banner */}
      {(details.error || details.status === 'failed') && (
        <div className="mb-8 bg-red-50 border-2 border-red-300 rounded-xl p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-red-100 text-red-800 rounded-lg shrink-0 mt-1">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold text-red-900 mb-1">Evaluation Pipeline Execution Failed</h3>
              <p className="text-sm text-red-800 whitespace-pre-line leading-relaxed">
                {details.error || 'The AI evaluation pipeline encountered an error processing this sheet.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stage 4: Educator Review / Override Panel */}
      {details.needs_human_review && (
        <div className="mb-8 bg-amber-50 border-2 border-amber-300 rounded-xl p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-amber-100 text-amber-800 rounded-lg shrink-0 mt-1">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>

            <div className="flex-1">
              <h3 className="text-lg font-bold text-amber-900 mb-1">
                ⚠️ Educator Verification Required (Stage 4 Flag)
              </h3>
              <ul className="list-disc list-inside text-sm text-amber-800 mb-4 space-y-0.5">
                {(details.review_reasons || ['Borderline score or handwriting uncertainty']).map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>

              <div className="bg-white border border-amber-200 rounded-lg p-4 max-w-xl">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">Educator Score Adjustment</h4>
                <div className="grid grid-cols-2 gap-4 mb-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Total Marks</label>
                    <input
                      type="number"
                      step="0.5"
                      value={overrideScore}
                      onChange={(e) => setOverrideScore(e.target.value)}
                      className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">Review Notes</label>
                    <input
                      type="text"
                      placeholder="e.g. Verified tree traversal by hand"
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Approving will clear the review flag and update the record.</span>
                  <button
                    onClick={handleResolveReview}
                    disabled={isSavingReview}
                    className="bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs px-5 py-2 rounded-lg transition-colors shadow-sm disabled:opacity-50"
                  >
                    {isSavingReview ? 'Saving...' : 'Confirm & Approve Score ✓'}
                  </button>
                </div>
              </div>

              {reviewSuccessMsg && (
                <p className="mt-3 text-sm font-semibold text-green-700">✓ {reviewSuccessMsg}</p>
              )}
            </div>
          </div>
        </div>
      )}


      {!evalData ? (
        <div className="bg-yellow-50 border-2 border-yellow-200 rounded-lg p-8 text-center">
          <p className="text-yellow-800 font-medium text-lg">Evaluation not yet completed for this script.</p>
          <p className="text-yellow-700 mt-2">{details.message}</p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-6 items-start">
          {/* Left Panel: Digitized Text & Parsed Diagrams */}
          <div className="space-y-6">
            {/* OCR Text Card */}
            <div className="bg-white border-2 border-slate-200 rounded-lg overflow-hidden flex flex-col shadow-sm">
              <div className="bg-slate-50 border-b border-slate-200 p-4">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-blue-100 text-blue-600 rounded">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-slate-800">Digitized Text & Math (Stage 1)</h2>
                    <p className="text-xs text-slate-500">Transcribed via Unified Qwen3-VL (8B)</p>
                  </div>
                </div>
              </div>

              <div className="p-5 bg-slate-50/50 max-h-[420px] overflow-y-auto">
                <pre className="font-mono text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                  {ocrText}
                </pre>
              </div>
            </div>

            {/* Stage 2 Diagram Descriptions Card */}
            {(figureCrops.length > 0 || details.diagram_description) && (
              <div className="bg-white border-2 border-indigo-200 rounded-lg overflow-hidden shadow-sm">
                <div className="bg-indigo-50 border-b border-indigo-200 p-4">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-indigo-100 text-indigo-700 rounded">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-indigo-950">Parsed Hand-Drawn Diagrams & State (Stage 2)</h2>
                      <p className="text-xs text-indigo-700">Structural trees, graphs & matrices translated by Qwen3-VL (8B)</p>
                    </div>
                  </div>
                </div>

                <div className="p-5 space-y-4">
                  {details.diagram_description && (
                    <div className="bg-indigo-50/40 border border-indigo-100 rounded-lg p-3">
                      <p className="text-xs font-bold text-indigo-800 mb-1">Structural Topology</p>
                      <pre className="font-mono text-xs text-slate-700 whitespace-pre-wrap leading-relaxed">
                        {details.diagram_description}
                      </pre>
                    </div>
                  )}
                  {figureCrops.map((crop, idx) => (
                    <div key={idx} className="bg-indigo-50/40 border border-indigo-100 rounded-lg p-3">
                      <p className="text-xs font-bold text-indigo-800 mb-1">Figure Block #{idx + 1}</p>
                      <pre className="font-mono text-xs text-slate-700 whitespace-pre-wrap">
                        {crop.diagram_description}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Panel: AI Scoring Breakdown */}
          <div className="flex flex-col gap-6">
            <div className="bg-white rounded-lg p-5 border-2 border-slate-200 shadow-sm flex justify-between items-center">
              <div>
                <h2 className="text-lg font-bold text-slate-800">AI Scoring Breakdown</h2>
                <p className="text-sm text-slate-500 mt-0.5">Question-level grading with model answer ground truth</p>
              </div>
              <div className="text-right">
                <span className="text-2xl font-bold text-slate-800">{evalData.questions.length}</span>
                <span className="text-sm text-slate-500 ml-1">Questions</span>
              </div>
            </div>

            <div className="space-y-5">
              {evalData.questions.map((q) => {
                const qPct = q.max_marks > 0 ? (q.total_marks / q.max_marks) * 100 : 0

                return (
                  <div
                    key={q.question_number}
                    className={`bg-white border-2 rounded-xl overflow-hidden shadow-sm transition-all hover:shadow-md ${getCategoryBadge(qPct)}`}
                  >
                    {/* Question Header */}
                    <div className="p-5 border-b border-black/5 bg-white/50">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="bg-slate-800 text-white text-xs font-bold px-2 py-1 rounded">Q{q.question_number}</span>
                          </div>
                          <h3 className="text-base font-semibold text-slate-800 leading-snug">
                            {q.question_text || 'Question ' + q.question_number}
                          </h3>
                        </div>
                        <div className="text-right shrink-0 bg-white px-3 py-2 rounded-lg border border-slate-200 shadow-sm">
                          <span className="text-2xl font-bold text-slate-800">
                            {q.total_marks}
                          </span>
                          <span className="text-sm text-slate-500 font-medium">/{q.max_marks}</span>
                        </div>
                      </div>
                    </div>

                    <div className="p-5">
                      {/* Sub-components if available */}
                      {q.component_scores && q.component_scores.length > 0 && (
                        <div className="mb-4 space-y-2.5">
                          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Rubric Assessment</h4>
                          {q.component_scores.map((comp, idx) => {
                            const compPct = comp.max_marks > 0 ? (comp.marks_awarded / comp.max_marks) * 100 : 0
                            return (
                              <div key={idx} className="bg-white border border-slate-100 rounded-lg p-3 shadow-sm">
                                <div className="flex justify-between items-center mb-1">
                                  <span className="text-sm font-semibold text-slate-700">{comp.component}</span>
                                  <span className="text-sm font-bold text-slate-800">{comp.marks_awarded} <span className="text-slate-400 font-normal">/ {comp.max_marks}</span></span>
                                </div>
                                <div className="w-full bg-slate-100 rounded-full h-1.5">
                                  <div
                                    className={`h-1.5 rounded-full ${getProgressColor(compPct)}`}
                                    style={{ width: `${compPct}%` }}
                                  ></div>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}

                      {/* Feedback */}
                      {q.feedback && (
                        <div>
                          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Evaluator Rationale</h4>
                          <div className="bg-white rounded-lg p-4 border border-slate-200 shadow-sm">
                            <div className="flex gap-3">
                              <svg className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                              </svg>
                              <p className="text-sm text-slate-700 leading-relaxed">
                                {q.feedback}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Idea 4: Side-by-Side View */}
                      <div className="mt-4 border-t border-slate-100 pt-4">
                        <button
                          onClick={() => setExpandedSideBySide(expandedSideBySide === q.question_number ? null : q.question_number)}
                          className="flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-900 transition-colors"
                        >
                          📋 Compare with Expected
                          <svg className={`w-4 h-4 transition-transform ${expandedSideBySide === q.question_number ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                        
                        {expandedSideBySide === q.question_number && (
                          <div className="mt-4 grid md:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
                            <div>
                              <h5 className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-2">Student Submission (Transcribed)</h5>
                              <div className="bg-white p-3 rounded-lg border border-slate-200 text-xs text-slate-700 max-h-56 overflow-y-auto whitespace-pre-wrap leading-relaxed font-mono">
                                {ocrText || q.feedback}
                              </div>
                            </div>
                            <div>
                              <h5 className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-2">Expected Answer Checklist</h5>
                              <div className="bg-white p-3 rounded-lg border border-slate-200 max-h-56 overflow-y-auto flex flex-col gap-2.5">
                                {q.component_scores && q.component_scores.length > 0 ? (
                                  q.component_scores.map((comp, idx) => (
                                    <div key={idx} className="flex items-start gap-2.5 text-xs pb-2 border-b border-slate-100 last:border-0 last:pb-0">
                                      <span className="shrink-0 mt-0.5 text-sm">
                                        {comp.marks_awarded >= comp.max_marks ? '✅' : '❌'}
                                      </span>
                                      <div className="flex-1">
                                        <div className="flex items-center justify-between font-semibold text-slate-800">
                                          <span>{comp.component}</span>
                                          <span className="text-slate-500 font-mono text-[11px]">{comp.marks_awarded} / {comp.max_marks}</span>
                                        </div>
                                        {comp.model_answer ? (
                                          <p className="text-slate-600 mt-1 italic leading-snug">{comp.model_answer}</p>
                                        ) : (
                                          <span className="italic text-slate-400">Standard criteria applied</span>
                                        )}
                                        {comp.feedback && (
                                          <p className="text-blue-700 text-[11px] mt-1 font-sans">Rationale: {comp.feedback}</p>
                                        )}
                                      </div>
                                    </div>
                                  ))
                                ) : (
                                  <span className="italic text-slate-400 text-xs">No components to compare.</span>
                                )}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ScriptDetails
