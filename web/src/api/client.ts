/** Typed API client — all calls go through /api (proxied to FastAPI on :8000). */

export interface InstanceSummary {
  name: string
  customers: number
  nfzs: number
  fleet: number | null
  battery: number
  payload: number
}

export interface NodeData {
  id: number
  x: number
  y: number
  z: number
  demand: number
}

export interface NFZData {
  id: number
  x_min: number
  x_max: number
  y_min: number
  y_max: number
  z_min: number
  z_max: number
}

export interface TerrainData {
  enabled: boolean
  x_size: number
  y_size: number
  height_map: number[][] | null
}

export interface InstanceDetail {
  metadata: Record<string, unknown>
  drone_profile: { payload_capacity: number; battery_capacity: number; fleet_size: number | null }
  depot: NodeData
  customers: NodeData[]
  no_fly_zones: NFZData[]
  terrain: TerrainData
}

export interface GAConfigOut {
  population_size: number
  generations: number
  tournament_size: number
  crossover_rate: number
  mutation_rate: number
  elitism: number
  no_improvement_generations: number
  fleet_penalty: number
  random_seed: number | null
  record_history: boolean
}

export interface SAConfigOut {
  initial_temperature: number
  min_temperature: number
  cooling_rate: number
  inner_iterations: number
  max_iterations: number
  no_improvement_window: number
  construction: string
  random_seed: number | null
  record_history: boolean
}

export interface RouteOut {
  drone_id: number
  customers: number[]
}

export interface SolutionOut {
  routes: RouteOut[]
  depot_zero_array: number[]
}

export interface HistoryEntry {
  iteration: number
  best_energy: number
  current_energy: number
  accepted: boolean
  temperature: number | null
}

export interface RunResult {
  run_id?: string
  algorithm: string
  instance_name: string
  best_energy: number
  feasible: boolean
  num_routes: number
  violations: string[]
  best_solution: SolutionOut
  iterations: number
  runtime_seconds: number
  config: Record<string, unknown>
  notes: Record<string, unknown>
  history: HistoryEntry[]
}

export interface RunStatus {
  run_id: string
  status: 'running' | 'done' | 'error'
  instance: string
  algorithm: string
  progress: number | null
  best_energy_so_far: number | null
  result: RunResult | null
  error: string | null
  started_at: number
  finished_at: number | null
}

export interface RunListItem {
  run_id: string
  instance: string
  algorithm: string
  energy: number | null
  drones: number | null
  runtime: number | null
  ts: number
  status: string
}

export interface ProgressEvent {
  type: 'progress' | 'done' | 'error'
  iteration: number
  best_energy: number
  temperature: number | null
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

async function get<T>(path: string): Promise<T> {
  const resp = await fetch(path)
  if (!resp.ok) throw new Error(`GET ${path} → ${resp.status}`)
  return resp.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`POST ${path} → ${resp.status}: ${text}`)
  }
  return resp.json()
}

export const api = {
  instances: {
    list: () => get<InstanceSummary[]>('/api/instances'),
    summary: (name: string) => get<InstanceSummary>(`/api/instances/${name}/summary`),
    detail: (name: string) => get<InstanceDetail>(`/api/instances/${name}`),
  },

  runs: {
    create: (body: { instance: string; algorithm: string; config: Record<string, unknown> }) =>
      post<{ run_id: string }>('/api/runs', body),
    get: (runId: string) => get<RunStatus>(`/api/runs/${runId}`),
    list: () => get<RunListItem[]>('/api/runs'),
  },

  /** Open an SSE stream for a run. Returns a cleanup function. */
  streamRun: (
    runId: string,
    onEvent: (ev: ProgressEvent) => void,
    onDone: () => void,
    onError: (err: Event) => void,
  ): (() => void) => {
    const es = new EventSource(`/api/runs/${runId}/stream`)
    es.onmessage = (e) => {
      const ev: ProgressEvent = JSON.parse(e.data)
      if (ev.type === 'done') {
        es.close()
        onDone()
      } else if (ev.type === 'error') {
        es.close()
        onError(e)
      } else {
        onEvent(ev)
      }
    }
    es.onerror = (e) => {
      es.close()
      onError(e)
    }
    return () => es.close()
  },
}
