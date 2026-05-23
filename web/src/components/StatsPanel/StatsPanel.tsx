/** Right-rail stats & telemetry panel. */

import type { InstanceDetail, ProgressEvent, RunResult } from '../../api/client'
import { DRONE_COLORS } from '../Map3D/palette'
import { ConvergenceChart } from './ConvergenceChart'
import { DroneCard } from './DroneCard'
import { HeadlineTiles } from './HeadlineTiles'

interface Props {
  result: RunResult | null
  instance: InstanceDetail | null
  liveEvents: ProgressEvent[]
  liveEnergy: number | null
  isRunning: boolean
  highlightedDrone: number | null
  onHighlightDrone: (idx: number | null) => void
  onCompare?: () => void
}

export function StatsPanel({
  result,
  instance,
  liveEvents,
  liveEnergy,
  isRunning,
  highlightedDrone,
  onHighlightDrone,
  onCompare,
}: Props) {
  if (!result && !isRunning) {
    return (
      <div className="flex items-center justify-center h-full text-slate-600 text-sm p-4 text-center">
        <div>
          <div className="text-2xl mb-2">◈</div>
          <div>Results will appear here once a run completes.</div>
        </div>
      </div>
    )
  }

  const warmStart = result?.history?.[0]?.best_energy

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4 min-h-0">
        {result && (
          <>
            {/* Headline tiles */}
            <HeadlineTiles
              result={result}
              liveEnergy={liveEnergy}
              isRunning={isRunning}
            />

            {/* Drone legend + cards */}
            {instance && result.best_solution.routes.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="label">Per-drone breakdown</span>
                  <span className="text-xs text-slate-500">click to isolate</span>
                </div>
                <div className="flex flex-wrap gap-1 mb-1">
                  {result.best_solution.routes.map((_, idx) => (
                    <button
                      key={idx}
                      onClick={() => onHighlightDrone(highlightedDrone === idx ? null : idx)}
                      className="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs transition-colors"
                      style={{
                        backgroundColor: highlightedDrone === idx
                          ? `${DRONE_COLORS[idx % DRONE_COLORS.length]}33`
                          : 'transparent',
                        borderWidth: 1,
                        borderColor: highlightedDrone === idx
                          ? DRONE_COLORS[idx % DRONE_COLORS.length]
                          : '#334155',
                        color: DRONE_COLORS[idx % DRONE_COLORS.length],
                      }}
                    >
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: DRONE_COLORS[idx % DRONE_COLORS.length] }} />
                      {idx + 1}
                    </button>
                  ))}
                </div>

                <div className="space-y-2">
                  {result.best_solution.routes.map((route, idx) => {
                    // Rough energy per route: proportional to route length
                    const perRoute = result.best_energy / result.best_solution.routes.length
                    return (
                      <DroneCard
                        key={idx}
                        route={route}
                        droneIndex={idx}
                        instance={instance}
                        battery={perRoute}
                        isHighlighted={highlightedDrone === idx}
                        onHighlight={onHighlightDrone}
                      />
                    )
                  })}
                </div>
              </div>
            )}

            {/* Compare button */}
            {onCompare && (
              <button onClick={onCompare} className="btn-ghost w-full text-sm border border-slate-700">
                ⊞ Compare with another run
              </button>
            )}
          </>
        )}

        {/* Live running hint */}
        {isRunning && !result && (
          <div className="tile flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shrink-0" />
            <span className="text-sm text-slate-300">Solver running…</span>
            {liveEnergy != null && (
              <span className="font-mono text-xs text-cyan-400 ml-auto">↓ {liveEnergy.toFixed(1)}</span>
            )}
          </div>
        )}
      </div>

      {/* Convergence chart — pinned to bottom */}
      <div className="shrink-0 h-44 border-t border-slate-800 p-1 bg-slate-950">
        <div className="label px-2 pt-1 pb-0.5">Convergence</div>
        <div className="h-36">
          <ConvergenceChart
            key={result?.algorithm ?? 'none'}
            history={result?.history ?? []}
            liveEvents={liveEvents}
            algorithm={result?.algorithm ?? 'sa'}
            warmStartEnergy={warmStart}
            color={DRONE_COLORS[0]}
          />
        </div>
      </div>
    </div>
  )
}
