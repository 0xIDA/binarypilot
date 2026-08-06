import { ChevronRight } from "lucide-react";
import type { RunListEntry, RunsPayload, RunSeverityCounts } from "@/data/serverSource";
import { runTitle } from "@/lib/target-utils";

/**
 * "Past runs" panel. The session cookie set by the local viewer process is the
 * only auth; there's no email-verification tier anymore. Clicking an entry
 * switches the active run and threads ?run=<name> through the data fetches.
 */

const SEV = [
  { key: "critical", dot: "bg-red-500", text: "text-red-500" },
  { key: "high", dot: "bg-orange-500", text: "text-orange-500" },
  { key: "medium", dot: "bg-yellow-500", text: "text-yellow-500" },
  { key: "low", dot: "bg-blue-500", text: "text-blue-500" },
] as const;

function SeverityChips({ counts }: { counts: RunSeverityCounts }) {
  const shown = SEV.filter((s) => counts[s.key] > 0);
  if (shown.length === 0) {
    return <span className="text-xs text-[#555]">No findings</span>;
  }
  return (
    <div className="flex items-center gap-3">
      {shown.map((s) => (
        <div key={s.key} className="flex items-center gap-1.5">
          <span className={`h-2 w-2 rounded-full ${s.dot}`} aria-hidden="true" />
          <span className={`text-xs tabular-nums ${s.text}`}>{counts[s.key]}</span>
        </div>
      ))}
    </div>
  );
}

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const normalized = iso.trim().replace(" UTC", "Z").replace(" ", "T");
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Relative time ("just now" / "5m ago" / "3h ago" / "2d ago"), falling back to
 * the absolute date for anything older than a week (mirrors the pro app).
 */
function formatTimeAgo(iso: string | null): string | null {
  if (!iso) return null;
  const normalized = iso.trim().replace(" UTC", "Z").replace(" ", "T");
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return null;
  const diffMs = Date.now() - d.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return formatDate(iso);
}

interface PastRunsViewProps {
  runs: RunsPayload | null;
  activeRun: string | null;
  onSelectRun: (name: string) => void;
}

export default function PastRunsView({
  runs,
  activeRun,
  onSelectRun,
}: PastRunsViewProps) {
  if (!runs || runs.runs.length === 0) {
    return (
      <div className="rounded-xl border border-[#222] bg-[rgba(255,255,255,0.02)] p-8 text-center text-sm text-[#888]">
        No past runs found on this machine yet.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {runs.runs.map((run: RunListEntry) => {
        const active = run.name === activeRun;
        const date = formatTimeAgo(run.start_time) ?? formatTimeAgo(run.end_time);
        const title = runTitle(run.target, run.name);
        return (
          <button
            key={run.name}
            onClick={() => onSelectRun(run.name)}
            className={`animate-card-in group flex w-full cursor-pointer items-center gap-4 rounded-lg border px-4 py-3 text-left transition-colors ${
              active
                ? "border-[#444] bg-[rgba(255,255,255,0.04)]"
                : "border-[#222] bg-[rgba(255,255,255,0.02)] hover:border-[#444]"
            }`}
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium text-white">{title}</span>
                {active && (
                  <span className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-400" style={{ border: "1px solid rgba(16,185,129,0.3)" }}>
                    Active
                  </span>
                )}
              </div>
              <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-[#666]">
                {run.scan_mode && <span className="capitalize">{run.scan_mode}</span>}
                {run.scan_mode && (date || run.status) && <span className="text-[#333]">·</span>}
                {date && <span>{date}</span>}
                {date && run.status && <span className="text-[#333]">·</span>}
                {run.status && <span className="capitalize">{run.status}</span>}
              </div>
            </div>
            <SeverityChips counts={run.severity_counts} />
            <ChevronRight className="h-4 w-4 flex-shrink-0 text-[#555] transition-colors group-hover:text-[#aaa]" aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}
