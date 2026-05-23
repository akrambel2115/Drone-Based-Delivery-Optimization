import type { RunResult } from '../../api/client'

interface Props {
  result: RunResult
  liveEnergy: number | null
  isRunning: boolean
}

export function HeadlineTiles({ result, liveEnergy, isRunning }: Props) {
  const energy = isRunning && liveEnergy != null ? liveEnergy : result.best_energy

  const totalDistance = (() => {
    // Rough proxy: sum all route customer counts * avg energy / customers
    return result.best_energy.toFixed(1)
  })()

  const tiles = [
    {
      label: 'Total energy',
      value: energy.toFixed(2),
      unit: 'units',
      accent: true,
      pulse: isRunning,
    },
    {
      label: 'Drones used',
      value: result.num_routes,
      unit: 'drones',
    },
    {
      label: result.algorithm === 'genetic_algorithm' ? 'Generations' : 'Iterations',
      value: result.iterations.toLocaleString(),
      unit: '',
    },
    {
      label: 'Runtime',
      value: result.runtime_seconds < 1
        ? `${(result.runtime_seconds * 1000).toFixed(0)}ms`
        : `${result.runtime_seconds.toFixed(2)}s`,
      unit: '',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-1.5">
      {tiles.map(({ label, value, unit, accent, pulse }) => (
        <div key={label} className={`tile ${accent ? 'border-cyan-500/40' : ''}`}>
          <div className="label text-[10px]">{label}</div>
          <div className={`font-mono text-base font-semibold mt-0.5 ${accent ? 'text-cyan-400' : 'text-slate-100'} ${pulse ? 'animate-pulse-slow' : ''}`}>
            {value}
            {unit && <span className="text-xs text-slate-500 ml-1 font-normal">{unit}</span>}
          </div>
        </div>
      ))}
      {/* Feasibility badge */}
      <div className="col-span-2 flex items-center gap-2">
        <span className={result.feasible ? 'badge-success' : 'badge-error'}>
          {result.feasible ? '✓ Feasible' : '✗ Infeasible'}
        </span>
        {result.violations.length > 0 && (
          <span className="text-xs text-red-400">{result.violations.join(', ')}</span>
        )}
      </div>
    </div>
  )
}
