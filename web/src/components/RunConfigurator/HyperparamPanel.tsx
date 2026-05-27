import { Tooltip } from '../shared/Tooltip'
import type { Algorithm } from './AlgoPicker'

// ---- Default configs ----

export const GA_DEFAULTS = {
  population_size: 40,
  generations: 200,
  tournament_size: 3,
  crossover_rate: 0.9,
  mutation_rate: 0.25,
  elitism: 2,
  no_improvement_generations: 0,
  fleet_penalty: 1000,
  random_seed: null as number | null,
  record_history: true,
}

export const SA_DEFAULTS = {
  initial_temperature: 100.0,
  min_temperature: 0.05,
  cooling_rate: 0.95,
  inner_iterations: 200,
  max_iterations: 50000,
  no_improvement_window: 0,
  construction: 'nearest_neighbor' as 'nearest_neighbor' | 'savings',
  random_seed: null as number | null,
  record_history: true,
}

export type GAConfig = typeof GA_DEFAULTS
export type SAConfig = typeof SA_DEFAULTS

// ---- Presets ----

const GA_PRESETS = {
  Faster: { population_size: 20, generations: 50, tournament_size: 2, crossover_rate: 0.8, mutation_rate: 0.3, elitism: 1, no_improvement_generations: 20, fleet_penalty: 1000, random_seed: null, record_history: true },
  Better: { population_size: 80, generations: 500, tournament_size: 4, crossover_rate: 0.95, mutation_rate: 0.15, elitism: 4, no_improvement_generations: 0, fleet_penalty: 1000, random_seed: null, record_history: true },
  Reproducible: { ...GA_DEFAULTS, random_seed: 42 },
}

const SA_PRESETS = {
  Faster: { ...SA_DEFAULTS, initial_temperature: 50, max_iterations: 10000, inner_iterations: 100 },
  Better: { ...SA_DEFAULTS, initial_temperature: 200, cooling_rate: 0.98, inner_iterations: 500, max_iterations: 200000 },
  Reproducible: { ...SA_DEFAULTS, random_seed: 42 },
}

// ---- Slider config ----

interface SliderSpec {
  key: string
  label: string
  tip: string
  min: number
  max: number
  step: number
  format?: (v: number) => string
}

const GA_SLIDERS: SliderSpec[] = [
  { key: 'population_size', label: 'Population size', tip: 'Number of chromosomes per generation.', min: 4, max: 200, step: 2 },
  { key: 'generations', label: 'Generations', tip: 'Maximum number of generations to run.', min: 10, max: 1000, step: 10 },
  { key: 'tournament_size', label: 'Tournament size', tip: 'Selection pressure — higher = greedier selection.', min: 2, max: 8, step: 1 },
  { key: 'crossover_rate', label: 'Crossover rate', tip: 'Probability of applying OX1 crossover to a parent pair.', min: 0, max: 1, step: 0.05, format: (v) => v.toFixed(2) },
  { key: 'mutation_rate', label: 'Mutation rate', tip: 'Probability of mutating each offspring.', min: 0, max: 1, step: 0.05, format: (v) => v.toFixed(2) },
  { key: 'elitism', label: 'Elitism', tip: 'Number of best chromosomes copied verbatim to the next generation.', min: 0, max: 10, step: 1 },
]

const SA_SLIDERS: SliderSpec[] = [
  { key: 'initial_temperature', label: 'Initial temperature', tip: 'Starting temperature T₀. Higher = more exploration at the start.', min: 1, max: 500, step: 1 },
  { key: 'cooling_rate', label: 'Cooling rate α', tip: 'Geometric factor: T ← α·T per plateau. Closer to 1 = slower cooling.', min: 0.8, max: 0.999, step: 0.001, format: (v) => v.toFixed(3) },
  { key: 'inner_iterations', label: 'Inner iterations', tip: 'Moves attempted at each temperature plateau.', min: 10, max: 2000, step: 10 },
  { key: 'max_iterations', label: 'Max iterations', tip: 'Hard cap on total proposed moves.', min: 1000, max: 200000, step: 1000 },
  { key: 'min_temperature', label: 'Min temperature', tip: 'Search stops when temperature falls below this value.', min: 0.001, max: 5, step: 0.001, format: (v) => v.toFixed(3) },
]

interface Props {
  algorithm: Algorithm
  gaConfig: GAConfig
  saConfig: SAConfig
  onGaChange: (c: GAConfig) => void
  onSaChange: (c: SAConfig) => void
}

function SliderRow({
  spec,
  value,
  onChange,
}: {
  spec: SliderSpec
  value: number
  onChange: (v: number) => void
}) {
  const display = spec.format ? spec.format(value) : String(value)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-300">{spec.label}</span>
          <Tooltip text={spec.tip} />
        </div>
        <span className="font-mono text-xs text-cyan-400 tabular-nums w-16 text-right">{display}</span>
      </div>
      <input
        type="range"
        min={spec.min}
        max={spec.max}
        step={spec.step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1 appearance-none bg-slate-700 rounded accent-cyan-500 cursor-pointer"
      />
    </div>
  )
}

export function HyperparamPanel({ algorithm, gaConfig, saConfig, onGaChange, onSaChange }: Props) {
  const sliders = algorithm === 'ga' ? GA_SLIDERS : SA_SLIDERS
  const config = algorithm === 'ga' ? gaConfig : saConfig
  const defaults = algorithm === 'ga' ? GA_DEFAULTS : SA_DEFAULTS
  const presets = algorithm === 'ga' ? GA_PRESETS : SA_PRESETS

  function updateKey(key: string, value: number | string | null) {
    if (algorithm === 'ga') onGaChange({ ...gaConfig, [key]: value } as GAConfig)
    else onSaChange({ ...saConfig, [key]: value } as SAConfig)
  }

  return (
    <div className="space-y-3">
      {/* Preset chips */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="label text-[10px]">Presets</span>
        {Object.entries(presets).map(([name, values]) => (
          <button
            key={name}
            onClick={() => algorithm === 'ga' ? onGaChange(values as GAConfig) : onSaChange(values as SAConfig)}
            className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors"
          >
            {name}
          </button>
        ))}
        <button
          onClick={() => algorithm === 'ga' ? onGaChange(GA_DEFAULTS) : onSaChange(SA_DEFAULTS)}
          className="px-2 py-0.5 rounded text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
        >
          Reset
        </button>
      </div>

      {/* Sliders */}
      <div className="space-y-3">
        {sliders.map((spec) => (
          <SliderRow
            key={spec.key}
            spec={spec}
            value={(config as Record<string, unknown>)[spec.key] as number}
            onChange={(v) => updateKey(spec.key, v)}
          />
        ))}
      </div>

      {/* Construction (SA only) */}
      {algorithm === 'sa' && (
        <div className="space-y-1">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-slate-300">Initial construction</span>
            <Tooltip text="How the initial solution is built. Nearest-neighbor is faster; savings often gives a better warm start." />
          </div>
          <select
            className="select w-full text-xs"
            value={(saConfig as SAConfig).construction}
            onChange={(e) => updateKey('construction', e.target.value)}
          >
            <option value="nearest_neighbor">Nearest Neighbor</option>
            <option value="savings">Clarke-Wright Savings</option>
          </select>
        </div>
      )}

      {/* Random seed */}
      <div className="space-y-1">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-300">Random seed</span>
          <Tooltip text="Set a seed for reproducible runs. Leave blank for a fresh random run." />
        </div>
        <input
          type="number"
          className="input w-full text-xs"
          placeholder="random"
          value={(config as Record<string, unknown>).random_seed as number ?? ''}
          onChange={(e) => updateKey('random_seed', e.target.value === '' ? null : parseInt(e.target.value))}
        />
      </div>
    </div>
  )
}
