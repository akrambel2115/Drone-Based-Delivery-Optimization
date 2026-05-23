import { useEffect } from 'react'
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import Cockpit from './pages/Cockpit'
import Compare from './pages/Compare'
import History from './pages/History'
import { ErrorBoundary } from './components/shared/ErrorBoundary'

const NAV_ITEMS = [
  { to: '/', label: 'Cockpit', icon: '⬡' },
  { to: '/compare', label: 'Compare', icon: '⊞' },
  { to: '/runs', label: 'History', icon: '◷' },
]

export default function App() {
  const navigate = useNavigate()

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return
      if (e.key >= '1' && e.key <= '9' && !e.ctrlKey && !e.metaKey) {
        navigate('/')
        // Instance quick-pick is handled in Cockpit via window event
        window.dispatchEvent(new CustomEvent('quickpick', { detail: { index: parseInt(e.key) - 1 } }))
      }
      if (e.key === '/' && !e.ctrlKey) {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('focus-dataset-search'))
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate])

  return (
    <div className="flex flex-col h-full bg-slate-950">
      {/* Top nav bar */}
      <header className="flex items-center gap-6 px-4 py-2 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 text-lg">◈</span>
          <span className="font-semibold text-slate-100 tracking-wide text-sm">Drone Cockpit</span>
        </div>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded text-sm transition-colors ${
                  isActive
                    ? 'bg-slate-700 text-slate-100'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`
              }
            >
              <span>{icon}</span>
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto text-xs text-slate-500 font-mono">
          Press <kbd className="bg-slate-800 px-1 rounded">1-9</kbd> to quick-pick instance
        </div>
      </header>

      <main className="flex-1 min-h-0">
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Cockpit />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/runs" element={<History />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  )
}
