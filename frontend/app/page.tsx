"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { SessionSummary } from "./types";
import { StatusBadge } from "./StatusBadge";

const ACTION_COLORS: Record<string, string> = {
  read_file:   "bg-sky-500",
  write_file:  "bg-violet-500",
  run_command: "bg-orange-500",
  llm_call:    "bg-emerald-500",
  unknown:     "bg-slate-500",
};

function ActionBar({ dist }: { dist: Record<string, number> }) {
  const total = Object.values(dist).reduce((a, b) => a + b, 0);
  if (!total) return null;
  return (
    <div className="flex h-1.5 rounded-full overflow-hidden w-full gap-px">
      {Object.entries(dist).map(([action, count]) => (
        <div
          key={action}
          className={`${ACTION_COLORS[action] ?? "bg-slate-500"} transition-all`}
          style={{ width: `${(count / total) * 100}%` }}
          title={`${action}: ${count}`}
        />
      ))}
    </div>
  );
}

function TimeAgo({ ts }: { ts: number }) {
  const diff = Math.floor(Date.now() / 1000 - ts);
  if (diff < 60) return <>{diff}s ago</>;
  if (diff < 3600) return <>{Math.floor(diff / 60)}m ago</>;
  return <>{Math.floor(diff / 3600)}h ago</>;
}

export default function HomePage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [lastRefresh, setLastRefresh] = useState(Date.now());

  const load = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/sessions");
      const data = await res.json();
      setSessions(data.sessions ?? []);
    } catch {
      // backend may not be running in preview
    } finally {
      setLoading(false);
      setLastRefresh(Date.now());
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  const filtered =
    filter === "all" ? sessions : sessions.filter((s) => s.status === filter);

  const counts = {
    all: sessions.length,
    healthy: sessions.filter((s) => s.status === "healthy").length,
    looping: sessions.filter((s) => s.status === "looping").length,
    drifting: sessions.filter((s) => s.status === "drifting").length,
    failing: sessions.filter((s) => s.status === "failing").length,
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Sessions</h1>
          <p className="text-sm text-[#94a3b8] mt-1">
            Real-time agent activity monitoring
          </p>
        </div>
        <button
          onClick={load}
          className="text-xs text-[#94a3b8] hover:text-white border border-[#2d3148] rounded-lg px-3 py-1.5 transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {(["all", "healthy", "looping", "drifting", "failing"] as const).map(
          (f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-lg text-sm transition-colors capitalize
                ${filter === f
                  ? "bg-indigo-600 text-white"
                  : "bg-[#1a1d27] text-[#94a3b8] hover:text-white border border-[#2d3148]"
                }`}
            >
              {f}
              <span className="ml-1.5 text-xs opacity-70">
                {counts[f] ?? 0}
              </span>
            </button>
          )
        )}
      </div>

      {/* Sessions grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="h-44 rounded-xl bg-[#1a1d27] border border-[#2d3148] animate-pulse"
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="text-4xl mb-4">🔭</div>
          <h2 className="text-lg font-semibold text-white mb-2">
            No sessions yet
          </h2>
          <p className="text-[#94a3b8] text-sm max-w-sm">
            Run the agent simulator to create sessions:
          </p>
          <pre className="mt-4 px-4 py-3 rounded-xl bg-[#1a1d27] border border-[#2d3148] text-xs text-emerald-400">
            python agent.py --scenario normal
          </pre>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((session) => (
            <Link
              key={session.session_id}
              href={`/sessions/${encodeURIComponent(session.session_id)}`}
              className="block group"
            >
              <div className="rounded-xl border border-[#2d3148] bg-[#1a1d27] p-5 hover:border-indigo-500/50 hover:bg-[#1e2235] transition-all duration-200">
                {/* Top row */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0 mr-3">
                    <p className="text-xs text-[#94a3b8] mb-0.5">Session ID</p>
                    <p className="font-mono text-sm text-white truncate">
                      {session.session_id}
                    </p>
                  </div>
                  <StatusBadge status={session.status} />
                </div>

                {/* Stats row */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="bg-[#0f1117] rounded-lg p-2 text-center">
                    <p className="text-lg font-bold text-white">
                      {session.total_steps}
                    </p>
                    <p className="text-[10px] text-[#94a3b8] uppercase tracking-wide">
                      Steps
                    </p>
                  </div>
                  <div className="bg-[#0f1117] rounded-lg p-2 text-center">
                    <p className="text-lg font-bold text-emerald-400">
                      {session.success_count}
                    </p>
                    <p className="text-[10px] text-[#94a3b8] uppercase tracking-wide">
                      OK
                    </p>
                  </div>
                  <div className="bg-[#0f1117] rounded-lg p-2 text-center">
                    <p className="text-lg font-bold text-red-400">
                      {session.failure_count}
                    </p>
                    <p className="text-[10px] text-[#94a3b8] uppercase tracking-wide">
                      Fail
                    </p>
                  </div>
                </div>

                {/* Action distribution bar */}
                <ActionBar dist={session.action_distribution} />

                {/* Issues */}
                {session.issues.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-[#2d3148]">
                    <p className="text-xs text-red-400 truncate">
                      ⚠ {session.issues[0]}
                    </p>
                  </div>
                )}

                {/* Footer */}
                <div className="mt-3 flex items-center justify-between text-[10px] text-[#4a5568]">
                  <span>
                    Updated <TimeAgo ts={session.last_updated} />
                  </span>
                  <span className="group-hover:text-indigo-400 transition-colors">
                    View details →
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="mt-8 p-4 rounded-xl bg-[#1a1d27] border border-[#2d3148]">
        <p className="text-xs text-[#94a3b8] mb-2 font-medium uppercase tracking-wide">
          Action Legend
        </p>
        <div className="flex flex-wrap gap-4">
          {Object.entries(ACTION_COLORS)
            .filter(([k]) => k !== "unknown")
            .map(([action, color]) => (
              <div key={action} className="flex items-center gap-1.5">
                <div className={`w-2.5 h-2.5 rounded-sm ${color}`} />
                <span className="text-xs text-[#94a3b8]">{action}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
