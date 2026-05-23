/** Showdown view — side-by-side comparison of two runs. */

import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { RunListItem, RunResult } from '../api/client'
import { ConvergenceChart } from '../components/StatsPanel/ConvergenceChart'
import { HeadlineTiles } from '../components/StatsPanel/HeadlineTiles'
import { DRONE_COLORS } from '../components/Map3D/palette'
import { useRunsStore } from '../store/runs'

export default function Compare() {
  const { compareA, compareB, setCompareA, setCompareB, lastResult } = useRunsStore()
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [loadingA, setLoadingA] = useState(false)
  const [loadingB, setLoadingB] = useState(false)

  useEffect(() => {
    api.runs.list().then((r) => setRuns(r.filter((x) => x.status === 'done'))).catch(console.error)
    // Pre-fill slot A with the last result if available
    if (!compareA && lastResult) setCompareA(lastResult)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadRun(runId: string, slot: 'A' | 'B') {
    const setter = slot === 'A' ? setLoadingA : setLoadingB
    setter(true)
    try {
      const status = await api.runs.get(runId)
      if (status.result) {
        if (slot === 'A') setCompareA(status.result)
        else setCompareB(status.result)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setter(false)
    }
  }

  return (
    <div className="p-4 h-full flex flex-col gap-4">
      <h1 className="text-lg font-semibold text-slate-100 shrink-0">Showdown</h1>

      <div className="flex gap-4 flex-1 min-h-0">
        {(['A', 'B'] as const).map((slot) => {
          const result = slot === 'A' ? compareA : compareB
          const loading = slot === 'A' ? loadingA : loadingB
          const color = slot === 'A' ? DRONE_COLORS[0] : DRONE_COLORS[1]

          return (
            <div key={slot} className="flex-1 card flex flex-col overflow-hidden">
              {/* Slot header */}
              <div className="flex items-center gap-2 p-3 border-b border-slate-700 shrink-0">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-sm font-semibold text-slate-300">Run {slot}</span>
                <select
                  className="select text-xs ml-auto"
                  value={result?.run_id ?? ''}
                  onChange={(e) => e.target.value && loadRun(e.target.value, slot)}
                  disabled={loading}
                >
                  <option value="">— pick a run —</option>
                  {runs.map((r) => (
                    <option key={r.run_id} value={r.run_id}>
                      {r.instance.replace('instance_', '').replace(/_/g, ' ')} / {r.algorithm?.toUpperCase()} / {r.energy?.toFixed(1)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-3 space-y-4 min-h-0">
                {loading && (
                  <div className="text-slate-500 text-sm text-center py-4">Loading…</div>
                )}
                {!loading && !result && (
                  <div className="text-slate-600 text-sm text-center py-8">
                    Select a run above
                  </div>
                )}
                {!loading && result && (
                  <>
                    <div className="space-y-1">
                      <div className="label">Instance</div>
                      <div className="font-mono text-xs text-slate-300">{result.instance_name}</div>
                    </div>
                    <HeadlineTiles result={result} liveEnergy={null} isRunning={false} />
                    <div>
                      <div className="label mb-1">Convergence</div>
                      <div className="h-44">
                        <ConvergenceChart
                          history={result.history}
                          liveEvents={[]}
                          algorithm={result.algorithm}
                          warmStartEnergy={result.history?.[0]?.best_energy}
                          color={color}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="label mb-1">Config</div>
                      <pre className="text-xs text-slate-400 bg-slate-950 rounded p-2 overflow-x-auto max-h-32">
                        {JSON.stringify(result.config, null, 2)}
                      </pre>
                    </div>
                  </>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Diff table */}
      {compareA && compareB && (
        <div className="card p-3 shrink-0">
          <div className="label mb-2">Δ Comparison</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 text-xs">
                <th className="text-left pb-1">Metric</th>
                <th className="text-right pb-1">Run A</th>
                <th className="text-right pb-1">Run B</th>
                <th className="text-right pb-1">Δ (A−B)</th>
                <th className="text-right pb-1">Winner</th>
              </tr>
            </thead>
            <tbody>
              {[
                {
                  label: 'Best energy',
                  a: compareA.best_energy,
                  b: compareB.best_energy,
                  fmt: (v: number) => v.toFixed(2),
                  lowerBetter: true,
                },
                {
                  label: 'Drones used',
                  a: compareA.num_routes,
                  b: compareB.num_routes,
                  fmt: (v: number) => String(v),
                  lowerBetter: true,
                },
                {
                  label: 'Runtime (s)',
                  a: compareA.runtime_seconds,
                  b: compareB.runtime_seconds,
                  fmt: (v: number) => v.toFixed(3),
                  lowerBetter: true,
                },
                {
                  label: 'Iterations',
                  a: compareA.iterations,
                  b: compareB.iterations,
                  fmt: (v: number) => v.toLocaleString(),
                  lowerBetter: false,
                },
              ].map(({ label, a, b, fmt, lowerBetter }) => {
                const delta = a - b
                const aWins = lowerBetter ? a < b : a > b
                return (
                  <tr key={label} className="border-t border-slate-800">
                    <td className="py-1.5 text-slate-400">{label}</td>
                    <td className="py-1.5 text-right font-mono text-sm text-slate-200">{fmt(a)}</td>
                    <td className="py-1.5 text-right font-mono text-sm text-slate-200">{fmt(b)}</td>
                    <td className={`py-1.5 text-right font-mono text-sm ${delta < 0 ? 'text-emerald-400' : delta > 0 ? 'text-red-400' : 'text-slate-500'}`}>
                      {delta > 0 ? '+' : ''}{fmt(delta)}
                    </td>
                    <td className="py-1.5 text-right">
                      <span style={{ color: aWins ? DRONE_COLORS[0] : DRONE_COLORS[1] }}>
                        {a === b ? '—' : aWins ? 'A' : 'B'}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
