import { FC, useEffect, useMemo, useState } from "react";

interface Props {
  status: "uploading" | "processing" | "ready" | "error";
  message: string;
  progress?: number;
  elapsedMs?: number;
  estimatedTotalMs?: number;
  estimatedRemainingMs?: number;
  completedInMs?: number;
  startedAtMs?: number;
  timingUpdatedAtMs?: number;
}

const formatDuration = (ms?: number) => {
  if (typeof ms !== "number" || ms < 0) return null;
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
};

/**
 * Format remaining duration as stable threshold labels so the display
 * doesn't feel like a countdown timer. Steps: almost done → ~15s →
 * ~30s → ~45s → ~1 min → ~1 min 30s → ~2 min → ~3 min → …
 */
const formatRemainingDuration = (ms?: number): string | null => {
  if (typeof ms !== "number" || ms < 0) return null;
  const s = Math.round(ms / 1000);
  if (s <= 5) return "almost done...";
  if (s <= 15) return "~15s";
  if (s <= 30) return "~30s";
  if (s <= 45) return "~45s";
  if (s <= 65) return "~1 min";
  if (s <= 100) return "~1 min 30s";
  if (s <= 140) return "~2 min";
  if (s <= 200) return "~3 min";
  if (s <= 260) return "~4 min";
  if (s <= 340) return "~5 min";
  // For longer durations round up to the nearest minute
  const mins = Math.ceil(s / 60);
  return `~${mins} min`;
};

export const StatusMessage: FC<Props> = ({
  status,
  message,
  progress,
  elapsedMs,
  estimatedTotalMs,
  estimatedRemainingMs,
  completedInMs,
  startedAtMs,
  timingUpdatedAtMs,
}) => {
  const getIcon = () => {
    switch (status) {
      case "uploading":
        return "📤";
      case "processing":
        return "⚙️";
      case "ready":
        return "✅";
      case "error":
        return "❌";
      default:
        return "ℹ️";
    }
  };

  const [tickNowMs, setTickNowMs] = useState<number>(Date.now());

  useEffect(() => {
    if (status !== "processing") {
      return;
    }
    const id = window.setInterval(() => {
      setTickNowMs(Date.now());
    }, 1000);
    return () => window.clearInterval(id);
  }, [status]);

  const dynamicTiming = useMemo(() => {
    if (status !== "processing") {
      return {
        elapsed: elapsedMs,
        remaining: estimatedRemainingMs,
      };
    }

    const baseElapsed = typeof elapsedMs === "number" ? elapsedMs : 0;
    const anchor = timingUpdatedAtMs ?? startedAtMs;
    const delta = anchor ? Math.max(0, tickNowMs - anchor) : 0;
    const elapsed = baseElapsed + delta;

    let remaining: number | undefined;
    if (typeof estimatedRemainingMs === "number") {
      remaining = Math.max(0, estimatedRemainingMs - delta);
    } else if (typeof estimatedTotalMs === "number") {
      remaining = Math.max(0, estimatedTotalMs - elapsed);
    }

    return {
      elapsed,
      remaining,
    };
  }, [status, elapsedMs, estimatedRemainingMs, estimatedTotalMs, timingUpdatedAtMs, startedAtMs, tickNowMs]);

  const elapsedLabel = formatDuration(dynamicTiming.elapsed);
  const remainingLabel = formatRemainingDuration(dynamicTiming.remaining);
  const totalLabel = formatRemainingDuration(estimatedTotalMs);
  const completedLabel = formatDuration(completedInMs);

  const getBackgroundColor = () => {
    switch (status) {
      case "uploading":
        return "bg-blue-50 border-blue-200";
      case "processing":
        return "bg-yellow-50 border-yellow-200";
      case "ready":
        return "bg-green-50 border-green-200";
      case "error":
        return "bg-red-50 border-red-200";
      default:
        return "bg-gray-50 border-gray-200";
    }
  };

  const getTextColor = () => {
    switch (status) {
      case "uploading":
        return "text-blue-800";
      case "processing":
        return "text-yellow-800";
      case "ready":
        return "text-green-800";
      case "error":
        return "text-red-800";
      default:
        return "text-gray-800";
    }
  };

  return (
    <div className="flex justify-center my-3">
      <div
        className={`${getBackgroundColor()} ${getTextColor()} border rounded-lg px-4 py-3 text-sm flex items-center gap-3 max-w-[85%] shadow-sm`}
      >
        <span className="text-xl flex-shrink-0">{getIcon()}</span>
        <div className="flex-1">
          <div>{message}</div>
          {progress !== undefined && status === "processing" && (
            <div className="mt-3">
              <div className="flex items-center gap-3">
                <div className="relative flex-1 bg-yellow-200 rounded-full h-2.5 overflow-hidden shadow-inner">
                  <div
                    className="absolute inset-0 bg-yellow-500 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${progress}%` }}
                  />
                  <div className="absolute inset-0 shimmer" />
                </div>
                <span className="text-xs font-bold min-w-[3rem] text-right tabular-nums">
                  {progress}%
                </span>
              </div>
            </div>
          )}
          {status === "processing" && (elapsedLabel || remainingLabel || totalLabel) && (
            <div className="mt-2 text-xs opacity-90">
              {elapsedLabel ? `Elapsed: ${elapsedLabel}` : "Elapsed: --"}
              {remainingLabel ? ` | Remaining: ${remainingLabel}` : ""}
              {!remainingLabel && totalLabel ? ` | Est. total: ${totalLabel}` : ""}
            </div>
          )}
          {status === "ready" && completedLabel && (
            <div className="mt-2 text-xs opacity-90">Completed in {completedLabel}</div>
          )}
        </div>
      </div>
    </div>
  );
};
