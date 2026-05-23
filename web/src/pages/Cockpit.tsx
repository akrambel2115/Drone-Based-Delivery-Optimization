/** Control Room — the main single-page app view. */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { InstanceDetail, RunResult } from '../api/client'
import { Map3D } from '../components/Map3D/Map3D'
import { RunConfigurator } from '../components/RunConfigurator'
import { StatsPanel } from '../components/StatsPanel/StatsPanel'
import { useRunsStore } from '../store/runs'

export default function Cockpit() {
  const navigate = useNavigate()
  const {
    selectedInstance,
    activeRunId,
    activeRunStatus,
    liveProgress,
    highlightedDrone,
    setActiveRunId,
    setActiveRunStatus,
    pushProgressEvent,
    clearLiveProgress,
    setHighlightedDrone,
    setLastResult,
  } = useRunsStore()

  const [instanceDetail, setInstanceDetail] = useState<InstanceDetail | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)
  const streamCleanupRef = useRef<(() => void) | null>(null)

  // Load instance detail when selection changes
  useEffect(() => {
    if (!selectedInstance) {
      setInstanceDetail(null)
      return
    }
    setResult(null)
    api.instances.detail(selectedInstance).then(setInstanceDetail).catch(console.error)
  }, [selectedInstance])

  // Keyboard shortcut C → Compare
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'INPUT') return
      if (e.key === 'c' && !e.ctrlKey && !e.metaKey && result) {
        navigate('/compare')
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate, result])

  const handleRunStarted = useCallback(
    (runId: string) => {
      setActiveRunId(runId)
      setActiveRunStatus({ run_id: runId, status: 'running', instance: selectedInstance ?? '', algorithm: '', progress: null, best_energy_so_far: null, result: null, error: null, started_at: Date.now() / 1000, finished_at: null })
      setResult(null)
      clearLiveProgress()

      // Close any existing stream
      streamCleanupRef.current?.()

      // Open SSE stream
      const cleanup = api.streamRun(
        runId,
        (ev) => pushProgressEvent(ev),
        async () => {
          // Stream done — fetch full result
          try {
            const status = await api.runs.get(runId)
            setActiveRunStatus(status)
            if (status.result) {
              const r = status.result as RunResult
              setResult(r)
              setLastResult(r)
            }
          } catch (err) {
            console.error('Failed to fetch run result:', err)
          }
        },
        (err) => {
          console.error('SSE error:', err)
          // Fallback: poll for completion
          const poll = setInterval(async () => {
            try {
              const status = await api.runs.get(runId)
              setActiveRunStatus(status)
              if (status.status !== 'running') {
                clearInterval(poll)
                if (status.result) {
                  const r = status.result as RunResult
                  setResult(r)
                  setLastResult(r)
                }
              }
            } catch {}
          }, 1000)
        },
      )
      streamCleanupRef.current = cleanup
    },
    [selectedInstance, setActiveRunId, setActiveRunStatus, clearLiveProgress, pushProgressEvent, setLastResult],
  )

  const isRunning = activeRunStatus?.status === 'running'

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left rail — Run Configurator */}
      <aside className="w-80 shrink-0 border-r border-slate-800 bg-slate-900/50 overflow-hidden flex flex-col">
        <RunConfigurator onRunStarted={handleRunStarted} />
      </aside>

      {/* Center — 3D map */}
      <main className="flex-1 min-w-0 overflow-hidden">
        <Map3D
          instance={instanceDetail}
          result={result}
          highlightedDrone={highlightedDrone}
        />
      </main>

      {/* Right rail — Stats & Telemetry */}
      <aside className="w-88 shrink-0 border-l border-slate-800 bg-slate-900/50 overflow-hidden flex flex-col" style={{ width: 352 }}>
        <div className="px-3 py-2 border-b border-slate-800 shrink-0">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Telemetry</h2>
        </div>
        <div className="flex-1 min-h-0">
          <StatsPanel
            result={result}
            instance={instanceDetail}
            liveEvents={liveProgress.events}
            liveEnergy={liveProgress.latestEnergy}
            isRunning={isRunning}
            highlightedDrone={highlightedDrone}
            onHighlightDrone={setHighlightedDrone}
            onCompare={result ? () => navigate('/compare') : undefined}
          />
        </div>
      </aside>
    </div>
  )
}
