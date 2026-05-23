/** Live convergence chart — best-energy vs iteration, with SA temperature on a secondary axis. */

import Plotly from 'plotly.js-dist-min'
import { useEffect, useRef } from 'react'
import type { HistoryEntry, ProgressEvent } from '../../api/client'

interface Props {
  history: HistoryEntry[]
  liveEvents: ProgressEvent[]
  algorithm: string
  warmStartEnergy?: number
  color?: string
}

export function ConvergenceChart({ history, liveEvents, algorithm, warmStartEnergy, color = '#00f5ff' }: Props) {
  const divRef = useRef<HTMLDivElement>(null)
  const initializedRef = useRef(false)
  const isSA = algorithm === 'simulated_annealing' || algorithm === 'sa'

  useEffect(() => {
    if (!divRef.current) return

    // Merge history + live events for the chart
    const hasHistory = history.length > 0
    const hasLive = liveEvents.length > 0

    let iterations: number[] = []
    let bestEnergies: number[] = []
    let temperatures: (number | null)[] = []

    if (hasHistory) {
      iterations = history.map((e) => e.iteration)
      bestEnergies = history.map((e) => e.best_energy)
      temperatures = history.map((e) => e.temperature ?? null)
    } else if (hasLive) {
      const progEvents = liveEvents.filter((e) => e.type === 'progress')
      iterations = progEvents.map((e) => e.iteration)
      bestEnergies = progEvents.map((e) => e.best_energy)
      temperatures = progEvents.map((e) => e.temperature ?? null)
    }

    if (iterations.length === 0) return

    const traces: Plotly.Data[] = [
      {
        type: 'scatter',
        x: iterations,
        y: bestEnergies,
        mode: 'lines',
        name: 'Best energy',
        line: { color, width: 2 },
        yaxis: 'y',
      } as Plotly.Data,
    ]

    if (isSA && temperatures.some((t) => t != null)) {
      traces.push({
        type: 'scatter',
        x: iterations,
        y: temperatures,
        mode: 'lines',
        name: 'Temperature',
        line: { color: '#f59e0b', width: 1, dash: 'dot' },
        opacity: 0.6,
        yaxis: 'y2',
      } as Plotly.Data)
    }

    // Warm-start reference line
    if (warmStartEnergy != null && iterations.length > 0) {
      traces.push({
        type: 'scatter',
        x: [iterations[0], iterations[iterations.length - 1]],
        y: [warmStartEnergy, warmStartEnergy],
        mode: 'lines',
        name: 'Warm start',
        line: { color: '#64748b', width: 1, dash: 'dash' },
        opacity: 0.5,
        yaxis: 'y',
      } as Plotly.Data)
    }

    const layout: Partial<Plotly.Layout> = {
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      margin: { l: 50, r: isSA ? 50 : 10, t: 10, b: 35 },
      font: { color: '#94a3b8', size: 10, family: 'JetBrains Mono' },
      xaxis: {
        title: algorithm === 'genetic_algorithm' ? 'Generation' : 'Iteration',
        gridcolor: '#1e293b',
        zerolinecolor: '#334155',
        tickfont: { size: 9 },
      },
      yaxis: {
        title: 'Best energy',
        gridcolor: '#1e293b',
        zerolinecolor: '#334155',
        tickfont: { size: 9 },
        side: 'left',
      },
      // Conditionally spread yaxis2 — never set to undefined; Plotly's cleanLayout
      // crashes trying to read .anchor from an undefined axis object.
      ...(isSA && temperatures.some((t) => t != null)
        ? {
            yaxis2: {
              title: 'Temperature',
              overlaying: 'y',
              side: 'right',
              gridcolor: 'transparent',
              tickfont: { size: 9, color: '#f59e0b' },
              titlefont: { color: '#f59e0b' },
            },
          }
        : {}),
      legend: {
        bgcolor: 'rgba(0,0,0,0)',
        borderwidth: 0,
        font: { size: 9 },
        x: 0.5,
        y: 1.0,
        xanchor: 'center',
        orientation: 'h',
      },
    }

    if (!initializedRef.current) {
      Plotly.newPlot(divRef.current, traces, layout, {
        displaylogo: false,
        responsive: true,
        displayModeBar: false,
      })
      initializedRef.current = true
    } else {
      Plotly.react(divRef.current, traces, layout)
    }
  }, [history, liveEvents, algorithm, color, isSA, warmStartEnergy])

  useEffect(() => {
    return () => {
      if (divRef.current && initializedRef.current) {
        Plotly.purge(divRef.current)
        initializedRef.current = false
      }
    }
  }, [])

  return <div ref={divRef} className="w-full h-full" />
}
