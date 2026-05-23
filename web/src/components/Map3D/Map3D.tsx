/** 3D mission map — Plotly surface + NFZ boxes + depot + customers + animated routes. */

import Plotly from 'plotly.js-dist-min'
import { useEffect, useRef, useState } from 'react'
import type { InstanceDetail, RunResult } from '../../api/client'
import { DRONE_COLORS } from './palette'

interface Props {
  instance: InstanceDetail | null
  result: RunResult | null
  highlightedDrone: number | null
}

const TERRAIN_COLORSCALE: [number, string][] = [
  [0.0, '#1a3a2a'],
  [0.28, '#2d6a4f'],
  [0.5, '#a7c957'],
  [0.72, '#7b4f2e'],
  [1.0, '#e8e0d4'],
]

export function Map3D({ instance, result, highlightedDrone }: Props) {
  const divRef = useRef<HTMLDivElement>(null)
  const plotReady = useRef<boolean>(false)
  // Use ref (not state) for animating flag to avoid stale closure issues
  const animatingRef = useRef<boolean>(false)
  const [showAnimBadge, setShowAnimBadge] = useState(false)
  // Track last animated result energy to avoid re-animating on highlight changes
  const lastAnimatedEnergy = useRef<number | null>(null)

  // Render / update the Plotly figure
  useEffect(() => {
    if (!divRef.current || !instance) return

    let traces: Plotly.Data[]
    let layout: Partial<Plotly.Layout>
    try {
      traces = buildTraces(instance, result, highlightedDrone)
      layout = buildLayout(instance)
    } catch (err) {
      console.error('Map3D buildTraces error:', err)
      return
    }

    const render = () => {
      if (!divRef.current) return
      try {
        if (!plotReady.current) {
          Plotly.newPlot(divRef.current, traces, layout, {
            displaylogo: false,
            responsive: true,
            modeBarButtonsToRemove: ['sendDataToCloud'],
          }).then(() => {
            plotReady.current = true
          })
        } else {
          Plotly.react(divRef.current, traces, layout)
        }
      } catch (err) {
        console.error('Map3D Plotly render error:', err)
      }
    }

    render()

    // Animate routes only when a genuinely new result arrives
    if (
      result &&
      !animatingRef.current &&
      result.best_energy !== lastAnimatedEnergy.current
    ) {
      lastAnimatedEnergy.current = result.best_energy
      animatingRef.current = true
      setShowAnimBadge(true)
      animateRoutes(divRef.current, instance, result, () => {
        animatingRef.current = false
        setShowAnimBadge(false)
      })
    }
  }, [instance, result?.best_energy, highlightedDrone]) // eslint-disable-line react-hooks/exhaustive-deps

  // Purge Plotly on unmount
  useEffect(() => {
    return () => {
      if (divRef.current && plotReady.current) {
        try {
          Plotly.purge(divRef.current)
        } catch (_) {
          // ignore purge errors on unmount
        }
        plotReady.current = false
      }
    }
  }, [])

  return (
    <div className="relative w-full h-full">
      <div ref={divRef} className="w-full h-full" />
      {!instance && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center space-y-2 opacity-50">
            <div className="text-4xl">◈</div>
            <div className="text-slate-400 text-sm">Select a dataset to see the map</div>
          </div>
        </div>
      )}
      {instance && !result && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
          <div className="bg-slate-900/80 backdrop-blur-sm border border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-400">
            Run a solver to plan delivery routes
          </div>
        </div>
      )}
      {showAnimBadge && (
        <div className="absolute top-3 right-3 flex items-center gap-1.5 bg-slate-900/80 border border-cyan-500/30 rounded px-2 py-1 text-xs text-cyan-400">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          Plotting routes…
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Terrain helper — produces x, y arrays and z[yi][xi] = height for Plotly
// ---------------------------------------------------------------------------

function buildTerrainArrays(
  hm: number[][],
  stride: number,
): { xVals: number[]; yVals: number[]; z: number[][] } {
  const xLen = hm.length
  const yLen = hm[0]?.length ?? 0
  const xVals: number[] = []
  const yVals: number[] = []
  // z[yi][xi] — outer y, inner x (Plotly Surface convention)
  const z: number[][] = []

  for (let yi = 0; yi < yLen; yi += stride) {
    yVals.push(yi)
    const row: number[] = []
    for (let xi = 0; xi < xLen; xi += stride) {
      if (yi === 0) xVals.push(xi)
      row.push(hm[xi]?.[yi] ?? 0)
    }
    z.push(row)
  }
  return { xVals, yVals, z }
}

// ---------------------------------------------------------------------------
// Trace builders
// ---------------------------------------------------------------------------

function buildTraces(
  instance: InstanceDetail,
  result: RunResult | null,
  highlightedDrone: number | null,
): Plotly.Data[] {
  const traces: Plotly.Data[] = []

  // Terrain surface
  const terrain = instance.terrain
  if (terrain.enabled && terrain.height_map && terrain.height_map.length > 0) {
    const hm = terrain.height_map
    const maxDim = Math.max(hm.length, hm[0]?.length ?? 0)
    const stride = Math.max(1, Math.floor(maxDim / 60))
    const { xVals, yVals, z } = buildTerrainArrays(hm, stride)
    traces.push({
      type: 'surface' as const,
      x: xVals,
      y: yVals,
      z: z as unknown as number[][],
      colorscale: TERRAIN_COLORSCALE,
      opacity: 0.88,
      name: 'terrain',
      showscale: false,
      hovertemplate: 'x=%{x} y=%{y} h=%{z:.0f}<extra>terrain</extra>',
      contours: { z: { show: false } },
    } as Plotly.Data)
  }

  // No-fly zones
  for (const nfz of instance.no_fly_zones) {
    traces.push(...buildNFZTraces(nfz))
  }

  // Node lookup
  const nodeMap: Record<number, { x: number; y: number; z: number; demand: number }> = {
    0: { ...instance.depot, demand: 0 },
  }
  for (const c of instance.customers) nodeMap[c.id] = c

  // Route assignment
  const customerRoute: Record<number, number> = {}
  if (result) {
    result.best_solution.routes.forEach((route, idx) => {
      route.customers.forEach((cid) => { customerRoute[cid] = idx })
    })
  }

  // Customers
  const demands = instance.customers.map((c) => c.demand)
  const minD = Math.min(...demands, 0)
  const maxD = Math.max(...demands, 1)
  const dRange = maxD - minD || 1

  const cxs: number[] = []
  const cys: number[] = []
  const czs: number[] = []
  const colors: string[] = []
  const sizes: number[] = []
  const texts: string[] = []

  for (const c of instance.customers) {
    cxs.push(c.x)
    cys.push(c.y)
    czs.push(c.z + 0.5)
    const routeIdx = customerRoute[c.id]
    const assigned = routeIdx != null
    const isHighlighted = highlightedDrone === routeIdx
    const isDimmed = highlightedDrone != null && !isHighlighted && assigned
    colors.push(
      isDimmed
        ? 'rgba(100,116,139,0.2)'
        : assigned
        ? DRONE_COLORS[routeIdx % DRONE_COLORS.length]
        : '#64748b',
    )
    sizes.push(7 + 8 * ((c.demand - minD) / dRange))
    texts.push(`Customer ${c.id}<br>demand=${c.demand}${assigned ? `<br>drone=${routeIdx + 1}` : ''}`)
  }

  traces.push({
    type: 'scatter3d' as const,
    x: cxs,
    y: cys,
    z: czs,
    mode: 'markers',
    marker: { color: colors, size: sizes, opacity: 0.92, line: { color: 'white', width: 0.7 } },
    name: 'customers',
    text: texts,
    hovertemplate: '%{text}<extra></extra>',
  } as Plotly.Data)

  // Depot
  traces.push({
    type: 'scatter3d' as const,
    x: [instance.depot.x],
    y: [instance.depot.y],
    z: [instance.depot.z + 1],
    mode: 'markers',
    marker: { color: '#ff3b30', size: 10, symbol: 'diamond', line: { color: 'white', width: 1.5 } },
    name: 'depot',
    text: [`Depot<br>x=${instance.depot.x} y=${instance.depot.y} z=${instance.depot.z}`],
    hovertemplate: '%{text}<extra></extra>',
  } as Plotly.Data)

  // Routes
  if (result) {
    result.best_solution.routes.forEach((route, idx) => {
      const color = DRONE_COLORS[idx % DRONE_COLORS.length]
      const nodeIds = [0, ...route.customers, 0]
      const rx = nodeIds.map((id) => nodeMap[id]?.x ?? 0)
      const ry = nodeIds.map((id) => nodeMap[id]?.y ?? 0)
      const rz = nodeIds.map((id) => (nodeMap[id]?.z ?? 0) + 1.5)
      const isDimmed = highlightedDrone != null && highlightedDrone !== idx
      traces.push({
        type: 'scatter3d' as const,
        x: rx,
        y: ry,
        z: rz,
        mode: 'lines',
        line: { color, width: isDimmed ? 1 : 3, dash: isDimmed ? 'dot' : 'solid' },
        opacity: isDimmed ? 0.15 : 0.85,
        name: `Drone ${idx + 1}`,
        hoverinfo: 'name',
      } as Plotly.Data)
    })
  }

  return traces
}

function buildNFZTraces(nfz: InstanceDetail['no_fly_zones'][0]): Plotly.Data[] {
  const { x_min, x_max, y_min, y_max, z_min, z_max } = nfz
  const x = [x_min, x_max, x_max, x_min, x_min, x_max, x_max, x_min]
  const y = [y_min, y_min, y_max, y_max, y_min, y_min, y_max, y_max]
  const z = [z_min, z_min, z_min, z_min, z_max, z_max, z_max, z_max]
  return [
    {
      type: 'mesh3d' as const,
      x, y, z,
      i: new Float64Array([0, 0, 0, 1, 4, 4, 5, 6, 2, 2, 3, 7]),
      j: new Float64Array([1, 2, 4, 5, 5, 6, 6, 7, 3, 6, 7, 4]),
      k: new Float64Array([2, 3, 5, 6, 6, 7, 7, 4, 6, 7, 0, 0]),
      color: '#ff3b30',
      opacity: 0.18,
      name: `NFZ ${nfz.id}`,
      hoverinfo: 'name',
      flatshading: true,
    } as unknown as Plotly.Data,
  ]
}

function buildLayout(instance: InstanceDetail): Partial<Plotly.Layout> {
  return {
    paper_bgcolor: 'rgba(2,6,23,0)',
    plot_bgcolor: 'rgba(2,6,23,0)',
    margin: { l: 0, r: 0, t: 0, b: 0 },
    legend: {
      bgcolor: 'rgba(15,23,42,0.85)',
      bordercolor: '#334155',
      borderwidth: 1,
      font: { color: '#94a3b8', size: 11 },
      x: 0.01,
      y: 0.99,
      xanchor: 'left',
      yanchor: 'top',
    },
    scene: {
      bgcolor: 'rgba(2,6,23,0)',
      xaxis: {
        title: 'x',
        gridcolor: '#1e293b',
        zerolinecolor: '#334155',
        tickfont: { color: '#475569', size: 9 },
        titlefont: { color: '#64748b' },
        range: [0, instance.terrain.x_size],
      },
      yaxis: {
        title: 'y',
        gridcolor: '#1e293b',
        zerolinecolor: '#334155',
        tickfont: { color: '#475569', size: 9 },
        titlefont: { color: '#64748b' },
        range: [0, instance.terrain.y_size],
      },
      zaxis: {
        title: 'z',
        gridcolor: '#1e293b',
        zerolinecolor: '#334155',
        tickfont: { color: '#475569', size: 9 },
        titlefont: { color: '#64748b' },
      },
      aspectmode: 'data',
      camera: { eye: { x: 1.4, y: -1.6, z: 1.1 } },
    },
  }
}

// ---------------------------------------------------------------------------
// Route animation — progressively reveals each drone's path
// ---------------------------------------------------------------------------

function animateRoutes(
  div: HTMLDivElement,
  instance: InstanceDetail,
  result: RunResult,
  onDone: () => void,
) {
  const nodeMap: Record<number, { x: number; y: number; z: number }> = { 0: instance.depot }
  for (const c of instance.customers) nodeMap[c.id] = c

  const routes = result.best_solution.routes
  const nfzCount = instance.no_fly_zones.length
  const hasTerrain = instance.terrain.enabled && !!instance.terrain.height_map
  // Prefix: terrain(0|1) + nfzs + customers(1) + depot(1)
  const prefixCount = (hasTerrain ? 1 : 0) + nfzCount + 2

  let completedRoutes = 0

  routes.forEach((route, routeIdx) => {
    const traceIdx = prefixCount + routeIdx
    const nodeIds = [0, ...route.customers, 0]
    const fullX = nodeIds.map((id) => nodeMap[id]?.x ?? 0)
    const fullY = nodeIds.map((id) => nodeMap[id]?.y ?? 0)
    const fullZ = nodeIds.map((id) => (nodeMap[id]?.z ?? 0) + 1.5)

    const DURATION_PER_DRONE = 1500
    const STAGGER = 350
    const delay = routeIdx * STAGGER
    let step = 1

    const tick = () => {
      if (!div.isConnected) return // guard against unmounted div
      try {
        Plotly.restyle(
          div,
          { x: [fullX.slice(0, step)], y: [fullY.slice(0, step)], z: [fullZ.slice(0, step)] },
          traceIdx,
        )
      } catch (err) {
        console.warn('animateRoutes restyle error:', err)
      }
      step++
      if (step <= fullX.length) {
        setTimeout(tick, DURATION_PER_DRONE / fullX.length)
      } else {
        completedRoutes++
        if (completedRoutes === routes.length) onDone()
      }
    }

    setTimeout(tick, delay)
  })

  // Edge case: no routes
  if (routes.length === 0) onDone()
}
