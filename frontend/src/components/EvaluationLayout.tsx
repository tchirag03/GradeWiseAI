import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

function EvaluationLayout() {
  return (
    <div className="flex min-h-screen bg-white">
      <Sidebar />

      <main className="flex-1 p-6 bg-slate-50">
        <Outlet />
      </main>
    </div>
  )
}

export default EvaluationLayout
