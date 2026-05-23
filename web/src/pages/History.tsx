/** Run history table — lists all past runs with click-to-restore. */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { RunListItem } from '../api/client'
import { useRunsStore } from '../store/runs'

export default function History() {
  const navigate = useNavigate()
  const { setSelectedInstance, setActiveRunId, setActiveRunStatus, setLastResult } = useRunsStore()
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.runs.list()
      .then(setRuns)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  async function openRun(run: RunListItem) {
    if (run.status !== 'done') return
    try {
      const status = await api.runs.get(run.run_id)
      setSelectedInstance(run.instance)
      setActiveRunId(run.run_id)
      setActiveRunStatus(status)
      if (status.result) setLastResult(status.result)
      navigate('/')
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-semibold text-slate-100 mb-4">Run History</h1>

      {loading && (
        <div className="text-slate-500 text-sm">Loading…</div>
      )}

      {!loading && runs.length === 0 && (
        <div className="tile text-slate-500 text-sm text-center py-8">
          No runs yet. Go to the Cockpit and launch a solver.
        </div>
      )}

      {runs.length > 0 && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400">
                {['Instance', 'Algorithm', 'Energy', 'Drones', 'Runtime', 'Date', 'Status'].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.run_id}
                  onClick={() => openRun(run)}
                  className={`border-b border-slate-800 transition-colors ${
                    run.status === 'done' ? 'hover:bg-slate-800/60 cursor-pointer' : 'opacity-60'
                  }`}
                >
                  <td className="px-4 py-3 font-mono text-xs text-slate-300">
                    {run.instance.replace('instance_', '').replace(/_/g, ' ')}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`badge-${run.algorithm === 'ga' ? 'success' : 'warning'}`}>
                      {run.algorithm?.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-200">
                    {run.energy != null ? run.energy.toFixed(2) : '—'}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-400">
                    {run.drones ?? '—'}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-400">
                    {run.runtime != null
                      ? run.runtime < 1
                        ? `${(run.runtime * 1000).toFixed(0)}ms`
                        : `${run.runtime.toFixed(2)}s`
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {run.ts ? new Date(run.ts * 1000).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        run.status === 'done'
                          ? 'badge-success'
                          : run.status === 'error'
                          ? 'badge-error'
                          : 'badge-warning'
                      }
                    >
                      {run.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
