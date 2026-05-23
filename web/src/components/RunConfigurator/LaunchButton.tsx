interface Props {
  running: boolean;
  disabled: boolean;
  progress: number | null;
  totalEstimate: number | null;
  bestEnergy: number | null;
  sparkline: number[];
  onLaunch: () => void;
}

export function LaunchButton({
  running,
  disabled,
  progress,
  totalEstimate,
  bestEnergy,
  sparkline,
  onLaunch,
}: Props) {
  const pct =
    progress != null && totalEstimate != null && totalEstimate > 0
      ? Math.min(100, Math.round((progress / totalEstimate) * 100))
      : null;

  if (!running) {
    return (
      <button
        className="btn-primary w-full py-3 text-base relative"
        onClick={onLaunch}
        disabled={disabled}
      >
        ▶ Launch
      </button>
    );
  }

  return (
    <div className="relative w-full rounded-lg overflow-hidden border border-cyan-500/50">
      {/* Progress bar track */}
      <div className="absolute inset-0 bg-slate-800" />
      {pct != null && (
        <div
          className="absolute inset-y-0 left-0 bg-cyan-500/20 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      )}

      {/* Content */}
      <div className="relative px-3 py-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shrink-0" />
          <span className="text-sm text-slate-200 font-medium truncate">
            {pct != null
              ? `${pct}% — iter ${progress?.toLocaleString()}`
              : "Starting…"}
          </span>
        </div>
        {bestEnergy != null && (
          <span className="font-mono text-xs text-cyan-400 shrink-0">
            ↓ {bestEnergy.toFixed(1)}
          </span>
        )}
      </div>

      {/* Mini sparkline */}
      {sparkline.length > 2 && (
        <div className="px-3 pb-1.5">
          <MiniSparkline values={sparkline} />
        </div>
      )}
    </div>
  );
}

function MiniSparkline({ values }: { values: number[] }) {
  const h = 20;
  const w = 280;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  });

  return (
    <svg
      width="100%"
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
    >
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke="#00f5ff"
        strokeWidth="1.5"
        opacity="0.7"
      />
    </svg>
  );
}
