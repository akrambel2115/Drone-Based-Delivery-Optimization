import { Tooltip } from '../shared/Tooltip'

export type Algorithm = 'ga' | 'sa'

interface Props {
  value: Algorithm
  onChange: (algo: Algorithm) => void
}

const ALGO_INFO: Record<Algorithm, string> = {
  ga: 'Genetic Algorithm — population-based search using crossover, mutation, and Prins optimal split decoding.',
  sa: 'Simulated Annealing — local search with Metropolis acceptance for escaping local optima.',
}

export function AlgoPicker({ value, onChange }: Props) {
  return (
    <div className="space-y-2">
      <label className="label">Algorithm</label>
      <div className="flex gap-1 bg-slate-900 border border-slate-700 rounded-lg p-1">
        {(['ga', 'sa'] as Algorithm[]).map((algo) => (
          <button
            key={algo}
            onClick={() => onChange(algo)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded text-sm font-semibold transition-colors ${
              value === algo
                ? 'bg-cyan-500 text-slate-950'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {algo.toUpperCase()}
            <Tooltip text={ALGO_INFO[algo]} />
          </button>
        ))}
      </div>
    </div>
  )
}
