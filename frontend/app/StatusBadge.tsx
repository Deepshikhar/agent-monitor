import { SessionStatus } from "@/lib/types";

const CONFIG: Record<
  SessionStatus,
  { label: string; bg: string; text: string; dot: string; icon: string }
> = {
  healthy:  { label: "Healthy",  bg: "bg-emerald-950", text: "text-emerald-400", dot: "bg-emerald-400", icon: "✓" },
  looping:  { label: "Looping",  bg: "bg-amber-950",   text: "text-amber-400",   dot: "bg-amber-400",   icon: "↻" },
  drifting: { label: "Drifting", bg: "bg-blue-950",    text: "text-blue-400",    dot: "bg-blue-400",    icon: "⇢" },
  failing:  { label: "Failing",  bg: "bg-red-950",     text: "text-red-400",     dot: "bg-red-400",     icon: "✗" },
};

export function StatusBadge({
  status,
  size = "sm",
}: {
  status: SessionStatus;
  size?: "sm" | "lg";
}) {
  const c = CONFIG[status] ?? CONFIG.healthy;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-medium
        ${c.bg} ${c.text} ${size === "lg" ? "text-sm px-3 py-1" : "text-xs"}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}
