import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import type { EvaluationFormData } from '@/types'
import { post } from '@/api/client'

interface CreateEvaluationApiResponse {
  id: string
  name: string
  subject: string
  max_marks: number
  answer_type: string
  status: string
}

function CreateEvaluation() {
  const navigate = useNavigate()

  const [formData, setFormData] = useState<EvaluationFormData>({
    evaluationName: '',
    courseSubject: '',
    maximumMarks: '',
    answerType: 'printed',
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.evaluationName.trim()) {
      newErrors.evaluationName = 'Evaluation name is required'
    }

    if (!formData.courseSubject.trim()) {
      newErrors.courseSubject = 'Course/Subject is required'
    }

    if (!formData.maximumMarks || parseInt(formData.maximumMarks) <= 0) {
      newErrors.maximumMarks = 'Maximum marks must be greater than 0'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()

    if (!validateForm()) return

    setIsSubmitting(true)
    try {
      const response = await post<CreateEvaluationApiResponse>('/evaluations', {
        name: formData.evaluationName.trim(),
        subject: formData.courseSubject.trim(),
        max_marks: parseInt(formData.maximumMarks),
        answer_type: formData.answerType,
      })

      // Navigate to upload page using the real MongoDB ID
      navigate(`/evaluation/${response.id}/upload`)
    } catch (err: any) {
      setErrors({ submit: err.message || 'Failed to create evaluation' })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Create New Evaluation</h1>
        <p className="text-slate-600">Set up a new evaluation session for your course assessment.</p>
      </div>

      {/* Form Card */}
      <div className="bg-white border-2 border-slate-200 rounded-lg shadow-lg p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Evaluation Name */}
          <div>
            <label htmlFor="evaluationName" className="block text-sm font-semibold text-slate-700 mb-2">
              Evaluation Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="evaluationName"
              name="evaluationName"
              value={formData.evaluationName}
              onChange={handleInputChange}
              placeholder="e.g., Mid-Term Exam 2024"
              className={`w-full px-4 py-3 border-2 rounded-lg focus:outline-none transition-colors ${errors.evaluationName
                ? 'border-red-500 focus:border-red-600'
                : 'border-slate-300 focus:border-blue-600'
                }`}
            />
            {errors.evaluationName && (
              <p className="mt-1 text-sm text-red-500">{errors.evaluationName}</p>
            )}
          </div>

          {/* Course/Subject */}
          <div>
            <label htmlFor="courseSubject" className="block text-sm font-semibold text-slate-700 mb-2">
              Course / Subject <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="courseSubject"
              name="courseSubject"
              value={formData.courseSubject}
              onChange={handleInputChange}
              placeholder="e.g., Mathematics, Computer Science"
              className={`w-full px-4 py-3 border-2 rounded-lg focus:outline-none transition-colors ${errors.courseSubject
                ? 'border-red-500 focus:border-red-600'
                : 'border-slate-300 focus:border-blue-600'
                }`}
            />
            {errors.courseSubject && (
              <p className="mt-1 text-sm text-red-500">{errors.courseSubject}</p>
            )}
          </div>

          {/* Maximum Marks */}
          <div>
            <label htmlFor="maximumMarks" className="block text-sm font-semibold text-slate-700 mb-2">
              Maximum Marks <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              id="maximumMarks"
              name="maximumMarks"
              value={formData.maximumMarks}
              onChange={handleInputChange}
              placeholder="e.g., 100"
              min="1"
              className={`w-full px-4 py-3 border-2 rounded-lg focus:outline-none transition-colors ${errors.maximumMarks
                ? 'border-red-500 focus:border-red-600'
                : 'border-slate-300 focus:border-blue-600'
                }`}
            />
            {errors.maximumMarks && (
              <p className="mt-1 text-sm text-red-500">{errors.maximumMarks}</p>
            )}
          </div>

          {/* Answer Type */}
          <div>
            <label htmlFor="answerType" className="block text-sm font-semibold text-slate-700 mb-2">
              Answer Type <span className="text-red-500">*</span>
            </label>
            <select
              id="answerType"
              name="answerType"
              value={formData.answerType}
              onChange={handleInputChange}
              className="w-full px-4 py-3 border-2 border-slate-300 rounded-lg focus:outline-none focus:border-blue-600 transition-colors bg-white"
            >
              <option value="printed">Printed</option>
              <option value="handwritten">Handwritten</option>
            </select>
          </div>

          {/* Server Error */}
          {errors.submit && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700">{errors.submit}</p>
            </div>
          )}

          {/* Form Actions */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={isSubmitting}
              className={`flex-1 font-semibold py-3 px-6 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg ${
                isSubmitting
                  ? 'bg-blue-400 cursor-not-allowed text-white'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {isSubmitting ? 'Creating...' : 'Create Evaluation'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/')}
              className="px-6 py-3 border-2 border-slate-300 text-slate-700 font-semibold rounded-lg hover:bg-slate-50 transition-colors duration-200"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>

      {/* Info Box */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex gap-3">
          <svg className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div className="text-sm text-blue-800">
            <p className="font-semibold mb-1">Note:</p>
            <p>After creating the evaluation, you'll be able to upload answer sheets, build rubrics, and process the evaluation offline.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CreateEvaluation
