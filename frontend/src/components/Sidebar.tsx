import { Link, useParams, useLocation } from 'react-router-dom'

function Sidebar() {
  const { evaluationId } = useParams<{ evaluationId: string }>()
  const location = useLocation()

  const navItems = [
    { label: 'Upload Sheets', path: `/evaluation/${evaluationId}/upload` },
    { label: 'Process Evaluation', path: `/evaluation/${evaluationId}/process` },
    { label: 'Results Overview', path: `/evaluation/${evaluationId}/results` },
    { label: 'Export Results', path: `/evaluation/${evaluationId}/export` },
  ]

  const isActive = (path: string) => location.pathname === path

  return (
    <aside className="w-64 bg-slate-800 text-white min-h-screen p-6">
      <div className="mb-8">
        <h2 className="text-lg font-bold text-blue-300">Evaluation Menu</h2>
        <p className="text-xs text-slate-400 mt-1">ID: {evaluationId}</p>
      </div>

      <nav className="space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`
              block px-4 py-3 rounded-lg transition-all duration-200
              ${isActive(item.path)
                ? 'bg-blue-600 text-white font-semibold shadow-lg'
                : 'bg-slate-700 text-slate-200 hover:bg-slate-600 hover:text-white'
              }
            `}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}

export default Sidebar
