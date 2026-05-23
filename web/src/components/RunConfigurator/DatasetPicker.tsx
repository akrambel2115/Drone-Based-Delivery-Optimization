import { useEffect, useRef } from 'react'
import type { InstanceSummary } from '../../api/client'

interface Props {
  instances: InstanceSummary[]
  selected: string | null
  onChange: (name: string) => void
}

export function DatasetPicker({ instances, selected, onChange }: Props) {
  const selectRef = useRef<HTMLSelectElement>(null)

  // Focus shortcut from App.tsx
  useEffect(() => {
    const handler = () => selectRef.current?.focus()
    window.addEventListener('focus-dataset-search', handler)
    return () => window.removeEventListener('focus-dataset-search', handler)
  }, [])

  // Quick-pick shortcut (1-9 keys)
  useEffect(() => {
    const handler = (e: Event) => {
      const { index } = (e as CustomEvent).detail
      if (index < instances.length) onChange(instances[index].name)
    }
    window.addEventListener('quickpick', handler)
    return () => window.removeEventListener('quickpick', handler)
  }, [instances, onChange])

  const summary = instances.find((i) => i.name === selected)

  return (
    <div className="space-y-2">
      <label className="label">Dataset</label>
      <select
        ref={selectRef}
        className="select w-full"
        value={selected ?? ''}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="" disabled>
          — pick an instance —
        </option>
        {instances.map((inst) => (
          <option key={inst.name} value={inst.name}>
            {inst.name.replace('instance_', '').replace(/_/g, ' ')} ({inst.customers} customers)
          </option>
        ))}
      </select>

      {summary && (
        <div className="grid grid-cols-2 gap-1.5 mt-2 animate-fade-in">
          {[
            ['Customers', summary.customers],
            ['No-fly zones', summary.nfzs],
            ['Fleet limit', summary.fleet ?? '∞'],
            ['Battery', summary.battery.toFixed(0)],
            ['Payload cap', summary.payload],
          ].map(([label, value]) => (
            <div key={String(label)} className="tile py-2">
              <div className="label text-[10px]">{label}</div>
              <div className="font-mono text-sm text-slate-100 mt-0.5">{value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
