"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { SessionDetail, AgentEvent } from "@/app/types";
import { StatusBadge } from "@/app/StatusBadge";
import { use } from "react";
// ─── Helpers ────────────────────────────────────────────────────────────────

const ACTION_CONFIG: Record<
  string,
  { icon: string; color: string; bg: string }
> = {
  read_file:   { icon: "📄", color: "text-sky-400",    bg: "bg-sky-950 border-sky-800" },
  write_file:  { icon: "✏️", color: "text-violet-400", bg: "bg-violet-950 border-violet-800" },
  run_command: { icon: "⚡", color: "text-orange-400", bg: "bg-orange-950 border-orange-800" },
  llm_call:    { icon: "🤖", color: "text-emerald-400",bg: "bg-emerald-950 border-emerald-800" },
  unknown:     { icon: "❓", color: "text-slate-400",  bg: "bg-slate-900 border-slate-700" },
};

function fmt(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

// ─── Event Card ─────────────────────────────────────────────────────────────

function EventCard({ event, index }: { event: AgentEvent; index: number }) {
  const [open, setOpen] = useState(false);
  const cfg = ACTION_CONFIG[event.action] ?? ACTION_CONFIG.unknown;
  const isFailure = event.metadata?.status === "failure";

  return (
    <div
      className={`rounded-lg border ${cfg.bg} transition-all duration-150`}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-start gap-3 p-3 text-left"
      >
        {/* Step number */}
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#0f1117] border border-[#2d3148] flex items-center justify-center">
          <span className="text-[10px] font-mono text-[#94a3b8]">
            {event.step ?? index + 1}
          </span>
        </div>

        {/* Icon + action */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm">{cfg.icon}</span>
            <span className={`text-xs font-semibold uppercase tracking-wide ${cfg.color}`}>
              {event.action}
            </span>
            {isFailure ? (
              <span className="ml-auto text-[10px] text-red-400 bg-red-950 border border-red-800 rounded px-1.5 py-0.5">
                FAIL
              </span>
            ) : (
              <span className="ml-auto text-[10px] text-emerald-400 bg-emerald-950 border border-emerald-800 rounded px-1.5 py-0.5">
                OK
              </span>
            )}
          </div>
          <p className="text-xs text-[#94a3b8] truncate">{event.input}</p>
        </div>

        {/* Time + expand */}
        <div className="flex-shrink-0 text-right">
          <p className="text-[10px] text-[#4a5568] font-mono">{fmt(event.timestamp)}</p>
          <p className="text-[10px] text-[#4a5568] mt-1">{open ? "▲" : "▼"}</p>
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-2 border-t border-[#2d3148]">
          <div className="mt-3">
            <p className="text-[10px] text-[#94a3b8] uppercase mb-1">Input</p>
            <pre className="text-xs text-white bg-[#0f1117] rounded-lg p-2 overflow-auto whitespace-pre-wrap max-h-32">
              {event.input || "—"}
            </pre>
          </div>
          <div>
            <p className="text-[10px] text-[#94a3b8] uppercase mb-1">Output</p>
            <pre className={`text-xs rounded-lg p-2 overflow-auto whitespace-pre-wrap max-h-32
              ${isFailure ? "text-red-300 bg-red-950/40" : "text-white bg-[#0f1117]"}`}>
              {event.output || "—"}
            </pre>
          </div>
          {event.metadata?.file && (
            <p className="text-[10px] text-[#94a3b8]">
              📁 {event.metadata.file}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function SessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetch(
        `http://localhost:8000/sessions/${encodeURIComponent(id)}`,
        { cache: "no-store" }
      );
      if (res.status === 404) {
        setNotFound(true);
        return;
      }
      const data = await res.json();
      setSession(data);
    } catch {
      // backend may not be running
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="animate-spin w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (notFound || !session) {
    return (
      <div className="text-center py-24">
        <p className="text-4xl mb-4">🔍</p>
        <h2 className="text-xl font-semibold text-white mb-2">Session not found</h2>
        <Link href="/" className="text-indigo-400 hover:underline text-sm">
          ← Back to sessions
        </Link>
      </div>
    );
  }

  const successRate = session.total_steps
    ? Math.round((session.success_count / session.total_steps) * 100)
    : 0;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-5 flex items-center gap-2 text-sm">
        <Link href="/" className="text-[#94a3b8] hover:text-white transition-colors">
          Sessions
        </Link>
        <span className="text-[#2d3148]">/</span>
        <span className="text-white font-mono truncate max-w-xs">{session.session_id}</span>
        <div className="ml-auto">
          <StatusBadge status={session.status} size="lg" />
        </div>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Steps",   value: session.total_steps,   color: "text-white" },
          { label: "Successes",     value: session.success_count,  color: "text-emerald-400" },
          { label: "Failures",      value: session.failure_count,  color: "text-red-400" },
          { label: "Success Rate",  value: `${successRate}%`,      color: successRate > 70 ? "text-emerald-400" : "text-red-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl bg-[#1a1d27] border border-[#2d3148] p-4">
            <p className="text-xs text-[#94a3b8] mb-1">{label}</p>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left: Event Timeline */}
        <div className="lg:col-span-2">
          <div className="rounded-xl bg-[#1a1d27] border border-[#2d3148] overflow-hidden">
            <div className="px-4 py-3 border-b border-[#2d3148] flex items-center justify-between">
              <h2 className="font-semibold text-white text-sm">Event Timeline</h2>
              <span className="text-xs text-[#94a3b8]">{session.events.length} events</span>
            </div>
            <div className="p-4 space-y-2 max-h-[700px] overflow-y-auto">
              {session.events.length === 0 ? (
                <p className="text-sm text-[#94a3b8] text-center py-8">
                  No events yet
                </p>
              ) : (
                session.events.map((event, i) => (
                  <EventCard key={`${event.step}-${i}`} event={event} index={i} />
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right: Issues + Insights + Distribution */}
        <div className="space-y-4">

          {/* Issues */}
          <div className="rounded-xl bg-[#1a1d27] border border-[#2d3148] overflow-hidden">
            <div className="px-4 py-3 border-b border-[#2d3148]">
              <h2 className="font-semibold text-white text-sm">Detected Issues</h2>
            </div>
            <div className="p-4">
              {session.issues.length === 0 ? (
                <div className="flex items-center gap-2 text-emerald-400">
                  <span className="text-lg">✓</span>
                  <span className="text-sm">No issues detected</span>
                </div>
              ) : (
                <ul className="space-y-2">
                  {session.issues.map((issue, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-xs text-[#e2e8f0] bg-red-950/30 border border-red-900/50 rounded-lg p-2.5"
                    >
                      <span className="text-red-400 mt-0.5 flex-shrink-0">⚠</span>
                      {issue}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Insights */}
          <div className="rounded-xl bg-[#1a1d27] border border-[#2d3148] overflow-hidden">
            <div className="px-4 py-3 border-b border-[#2d3148]">
              <h2 className="font-semibold text-white text-sm">Insights</h2>
            </div>
            <div className="p-4">
              <ul className="space-y-2">
                {session.insights.map((insight, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-xs text-[#94a3b8] bg-[#0f1117] rounded-lg p-2.5"
                  >
                    <span className="text-indigo-400 mt-0.5 flex-shrink-0">→</span>
                    {insight}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Action Distribution */}
          <div className="rounded-xl bg-[#1a1d27] border border-[#2d3148] overflow-hidden">
            <div className="px-4 py-3 border-b border-[#2d3148]">
              <h2 className="font-semibold text-white text-sm">Action Distribution</h2>
            </div>
            <div className="p-4 space-y-3">
              {Object.entries(session.action_distribution)
                .sort(([, a], [, b]) => b - a)
                .map(([action, count]) => {
                  const pct = Math.round((count / session.total_steps) * 100);
                  const COLOR_MAP: Record<string, string> = {
                    read_file: "bg-sky-500",
                    write_file: "bg-violet-500",
                    run_command: "bg-orange-500",
                    llm_call: "bg-emerald-500",
                    unknown: "bg-slate-500",
                  };
                  return (
                    <div key={action}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">{action}</span>
                        <span className="text-white font-mono">
                          {count} ({pct}%)
                        </span>
                      </div>
                      <div className="h-1.5 bg-[#0f1117] rounded-full overflow-hidden">
                        <div
                          className={`h-full ${COLOR_MAP[action] ?? "bg-slate-500"} rounded-full`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* Quick nav back */}
          <Link
            href="/"
            className="block text-center text-sm text-[#94a3b8] hover:text-white border border-[#2d3148] rounded-xl py-2.5 transition-colors"
          >
            ← All Sessions
          </Link>
        </div>
      </div>
    </div>
  );
}
