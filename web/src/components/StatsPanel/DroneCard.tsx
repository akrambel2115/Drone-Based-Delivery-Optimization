import type { InstanceDetail, RouteOut } from '../../api/client'
import { DRONE_COLORS } from '../Map3D/palette'

interface Props {
  route: RouteOut
  droneIndex: number
  instance: InstanceDetail
  battery: number
  isHighlighted: boolean
  onHighlight: (idx: number | null) => void
}

export function DroneCard({ route, droneIndex, instance, battery, isHighlighted, onHighlight }: Props) {
  const color = DRONE_COLORS[droneIndex % DRONE_COLORS.length]

  // Build lookup map for customer demands
  const demandMap: Record<number, number> = {}
  for (const c of instance.customers) demandMap[c.id] = c.demand

  const totalDemand = route.customers.reduce((s, id) => s + (demandMap[id] ?? 0), 0)
  const payloadCap = instance.drone_profile.payload_capacity
  const batteryCap = instance.drone_profile.battery_capacity
  const payloadPct = payloadCap > 0 ? Math.min(100, (totalDemand / payloadCap) * 100) : 0
  const batteryPct = batteryCap > 0 ? Math.min(100, (battery / batteryCap) * 100) : 0

  return (
    <div
      className={`card p-3 cursor-pointer transition-all duration-150 ${
        isHighlighted ? 'border-[color:var(--drone-color)] ring-1 ring-[color:var(--drone-color)]' : 'hover:border-slate-600'
      }`}
      style={{ '--drone-color': color } as React.CSSProperties}
      onClick={() => onHighlight(isHighlighted ? null : droneIndex)}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: color }} />
          <span className="text-sm font-semibold text-slate-100">Drone {droneIndex + 1}</span>
        </div>
        <span className="text-xs text-slate-400">{route.customers.length} stops</span>
      </div>

      {/* Payload bar */}
      <div className="space-y-1 mb-2">
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>Payload</span>
          <span className="font-mono text-slate-400">{totalDemand} / {payloadCap}</span>
        </div>
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${payloadPct}%`, backgroundColor: color, opacity: 0.8 }}
          />
        </div>
      </div>

      {/* Battery gauge */}
      <div className="space-y-1 mb-2">
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>Energy</span>
          <span className="font-mono text-slate-400">{battery.toFixed(1)} / {batteryCap.toFixed(0)}</span>
        </div>
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${batteryPct}%`, backgroundColor: batteryPct < 30 ? '#ef4444' : batteryPct < 60 ? '#f59e0b' : color, opacity: 0.8 }}
          />
        </div>
      </div>

      {/* Customer chips */}
      <div className="flex flex-wrap gap-1">
        {route.customers.map((cid) => (
          <span
            key={cid}
            className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium"
            style={{ backgroundColor: `${color}22`, color, border: `1px solid ${color}44` }}
          >
            C{cid}
          </span>
        ))}
      </div>
    </div>
  )
}
