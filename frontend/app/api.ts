const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchSessions() {
  const res = await fetch(`${API}/sessions`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

export async function fetchSession(id: string) {
  const res = await fetch(`${API}/sessions/${encodeURIComponent(id)}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error("Failed to fetch session");
  }
  return res.json();
}
