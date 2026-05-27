import { useState, useRef } from 'react'

interface TooltipProps {
  text: string
  children?: React.ReactNode
}

export function Tooltip({ text, children }: TooltipProps) {
  const [visible, setVisible] = useState(false)
  const ref = useRef<HTMLSpanElement>(null)

  return (
    <span
      ref={ref}
      className="relative inline-flex items-center cursor-help"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children ?? (
        <span className="w-4 h-4 rounded-full bg-slate-700 text-slate-400 text-[10px] flex items-center justify-center font-bold">
          ?
        </span>
      )}
      {visible && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-50 w-48 px-2 py-1.5 rounded bg-slate-700 border border-slate-600 text-xs text-slate-200 shadow-xl pointer-events-none">
          {text}
        </span>
      )}
    </span>
  )
}
