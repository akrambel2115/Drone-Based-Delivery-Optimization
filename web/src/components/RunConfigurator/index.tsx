/** Run Configurator — left rail of the Cockpit layout. */

import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import { useRunsStore } from '../../store/runs'
import type { Algorithm } from './AlgoPicker'
import { AlgoPicker } from './AlgoPicker'
import { DatasetPicker } from './DatasetPicker'
import { GA_DEFAULTS, HyperparamPanel, SA_DEFAULTS, BB_DEFAULTS } from './HyperparamPanel'
import type { GAConfig, SAConfig, BBConfig } from './HyperparamPanel'
import { LaunchButton } from './LaunchButton'

interface Props {
  onRunStarted: (runId: string, algo: Algorithm) => void
}

export function RunConfigurator({ onRunStarted }: Props) {
  const { instances, setInstances, selectedInstance, setSelectedInstance } = useRunsStore()
  const { activeRunStatus, liveProgress } = useRunsStore()
  const [algorithm, setAlgorithm] = useState<Algorithm>('sa')
  const [gaConfig, setGaConfig] = useState<GAConfig>(GA_DEFAULTS)
  const [saConfig, setSaConfig] = useState<SAConfig>(SA_DEFAULTS)
  const [bbConfig, setBbConfig] = useState<BBConfig>(BB_DEFAULTS)
  const [launching, setLaunching] = useState(false)
  const lastRunConfig = useRef<{ algorithm: Algorithm; gaConfig: GAConfig; saConfig: SAConfig; bbConfig: BBConfig } | null>(null)

  // Load instances once
  useEffect(() => {
    if (instances.length === 0) {
      api.instances.list().then(setInstances).catch(console.error)
    }
  }, [instances.length, setInstances])

  // Keyboard shortcut: R to re-run with same config
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'INPUT') return
      if (e.key === 'r' && !e.ctrlKey && !e.metaKey && !e.altKey && lastRunConfig.current) {
        const { algorithm: algo, gaConfig: ga, saConfig: sa, bbConfig: bb } = lastRunConfig.current
        setAlgorithm(algo)
        setGaConfig(ga)
        setSaConfig(sa)
        setBbConfig(bb)
        handleLaunch(algo, ga, sa, bb)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [selectedInstance]) // eslint-disable-line react-hooks/exhaustive-deps

  const isRunning = activeRunStatus?.status === 'running'
  const sparkline = liveProgress.events
    .filter((e) => e.type === 'progress')
    .map((e) => e.best_energy)

  const totalEstimate = algorithm === 'ga'
    ? gaConfig.generations
    : algorithm === 'sa' ? Math.ceil(saConfig.max_iterations / 50) : 100 // Arbitrary for BB

  async function handleLaunch(
    algo = algorithm,
    ga = gaConfig,
    sa = saConfig,
    bb = bbConfig,
  ) {
    if (!selectedInstance || launching || isRunning) return
    setLaunching(true)
    lastRunConfig.current = { algorithm: algo, gaConfig: ga, saConfig: sa, bbConfig: bb }
    try {
      const config = algo === 'ga' ? ga : algo === 'sa' ? sa : bb
      const { run_id } = await api.runs.create({
        instance: selectedInstance,
        algorithm: algo,
        config: config as Record<string, unknown>,
      })
      onRunStarted(run_id, algo)
    } catch (err) {
      console.error('Failed to create run:', err)
    } finally {
      setLaunching(false)
    }
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto p-3 gap-4">
      <div className="space-y-1">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Configure</h2>
      </div>

      <DatasetPicker
        instances={instances}
        selected={selectedInstance}
        onChange={setSelectedInstance}
      />

      <div className="border-t border-slate-700" />

      <AlgoPicker value={algorithm} onChange={setAlgorithm} />

      <HyperparamPanel
        algorithm={algorithm}
        gaConfig={gaConfig}
        saConfig={saConfig}
        bbConfig={bbConfig}
        onGaChange={setGaConfig}
        onSaChange={setSaConfig}
        onBbChange={setBbConfig}
      />

      <div className="border-t border-slate-700" />

      <LaunchButton
        running={isRunning}
        disabled={!selectedInstance || launching}
        progress={liveProgress.events.filter((e) => e.type === 'progress').length * (algorithm === 'ga' ? 1 : algorithm === 'sa' ? 50 : 1)}
        totalEstimate={algorithm === 'ga' ? gaConfig.generations : algorithm === 'sa' ? saConfig.max_iterations : liveProgress.events.filter((e) => e.type === 'progress').length + 10}
        bestEnergy={liveProgress.latestEnergy}
        sparkline={sparkline}
        onLaunch={() => handleLaunch()}
      />

      <div className="text-xs text-slate-600 text-center pb-1">
        Press <kbd className="bg-slate-800 px-1 rounded text-slate-500">R</kbd> to re-run same config
      </div>
    </div>
  )
}
