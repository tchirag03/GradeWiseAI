import { Routes, Route, Navigate } from 'react-router-dom'

import Home from './pages/Home'
import CreateEvaluation from './pages/CreateEvaluation'
import OpenEvaluation from './pages/OpenEvaluation'
import UploadSheets from './pages/UploadSheets'
import ProcessEvaluation from './pages/ProcessEvaluation'
import ResultsOverview from './pages/ResultsOverview'
import ScriptDetails from './pages/ScriptDetails'
import ExportResults from './pages/ExportResults'
import Settings from './pages/Settings'
import NotFound from './pages/NotFound'

import Layout from './components/Layout'
import EvaluationLayout from './components/EvaluationLayout'

function App() {
  return (
    <Routes>

      {/* Global App Layout */}
      <Route element={<Layout />}>

        {/* Home / Landing */}
        <Route path="/" element={<Home />} />
        <Route path="/evaluations" element={<Navigate to="/" replace />} />

        {/* Create or open an evaluation */}
        <Route path="/evaluation/new" element={<CreateEvaluation />} />
        <Route path="/evaluations/new" element={<Navigate to="/evaluation/new" replace />} />
        <Route path="/evaluation/:evaluationId/open" element={<OpenEvaluation />} />
        <Route path="/evaluations/:evaluationId/open" element={<OpenEvaluation />} />

        {/* Evaluation-scoped routes (canonical: /evaluation/:evaluationId) */}
        <Route
          path="/evaluation/:evaluationId"
          element={<EvaluationLayout />}
        >
          <Route index element={<Navigate to="results" replace />} />
          <Route path="upload" element={<UploadSheets />} />
          <Route path="process" element={<ProcessEvaluation />} />
          <Route path="results" element={<ResultsOverview />} />
          <Route path="results/:scriptId" element={<ScriptDetails />} />
          <Route path="export" element={<ExportResults />} />
        </Route>

        {/* Evaluation-scoped routes (plural alias: /evaluations/:evaluationId) */}
        <Route
          path="/evaluations/:evaluationId"
          element={<EvaluationLayout />}
        >
          <Route index element={<Navigate to="results" replace />} />
          <Route path="upload" element={<UploadSheets />} />
          <Route path="process" element={<ProcessEvaluation />} />
          <Route path="results" element={<ResultsOverview />} />
          <Route path="results/:scriptId" element={<ScriptDetails />} />
          <Route path="export" element={<ExportResults />} />
        </Route>

        {/* App-level settings */}
        <Route path="/settings" element={<Settings />} />

        {/* Fallback */}
        <Route path="*" element={<NotFound />} />

      </Route>

    </Routes>
  )
}

export default App
