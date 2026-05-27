/** Zustand store — tracks the active run, live progress, and comparison state. */

import { create } from 'zustand'
import type { InstanceSummary, ProgressEvent, RunResult, RunStatus } from '../api/client'

export interface LiveProgress {
  events: ProgressEvent[]
  latestEnergy: number | null
  latestTemperature: number | null
}

interface RunsStore {
  // Instance list
  instances: InstanceSummary[]
  setInstances: (list: InstanceSummary[]) => void

  // Active instance selection
  selectedInstance: string | null
  setSelectedInstance: (name: string) => void

  // Active run
  activeRunId: string | null
  activeRunStatus: RunStatus | null
  liveProgress: LiveProgress
  setActiveRunId: (id: string | null) => void
  setActiveRunStatus: (status: RunStatus | null) => void
  pushProgressEvent: (ev: ProgressEvent) => void
  clearLiveProgress: () => void

  // Highlighted drone (for cross-linking map ↔ stat cards)
  highlightedDrone: number | null
  setHighlightedDrone: (id: number | null) => void

  // Compare view: two run results loaded from disk
  compareA: RunResult | null
  compareB: RunResult | null
  setCompareA: (r: RunResult | null) => void
  setCompareB: (r: RunResult | null) => void

  // Last successful result (for "Compare with last run" shortcut)
  lastResult: RunResult | null
  setLastResult: (r: RunResult) => void
}

export const useRunsStore = create<RunsStore>((set) => ({
  instances: [],
  setInstances: (list) => set({ instances: list }),

  selectedInstance: null,
  setSelectedInstance: (name) => set({ selectedInstance: name }),

  activeRunId: null,
  activeRunStatus: null,
  liveProgress: { events: [], latestEnergy: null, latestTemperature: null },
  setActiveRunId: (id) => set({ activeRunId: id }),
  setActiveRunStatus: (status) => set({ activeRunStatus: status }),
  pushProgressEvent: (ev) =>
    set((state) => ({
      liveProgress: {
        events: [...state.liveProgress.events, ev],
        latestEnergy: ev.best_energy ?? state.liveProgress.latestEnergy,
        latestTemperature: ev.temperature ?? state.liveProgress.latestTemperature,
      },
    })),
  clearLiveProgress: () =>
    set({ liveProgress: { events: [], latestEnergy: null, latestTemperature: null } }),

  highlightedDrone: null,
  setHighlightedDrone: (id) => set({ highlightedDrone: id }),

  compareA: null,
  compareB: null,
  setCompareA: (r) => set({ compareA: r }),
  setCompareB: (r) => set({ compareB: r }),

  lastResult: null,
  setLastResult: (r) => set({ lastResult: r }),
}))
