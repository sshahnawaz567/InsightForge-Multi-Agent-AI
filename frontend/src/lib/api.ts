/**
 * Client for the real InsightForge FastAPI backend (backend/main.py).
 * Set VITE_API_URL to override the default local dev URL.
 */
import type { AnalysisResponse } from "@/components/insight-card";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) return false;
    const data = await res.json();
    return data.status === "healthy";
  } catch {
    return false;
  }
}

export async function askInsightForge(
  query: string,
  sessionId?: string,
): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId ?? null }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.error ?? `Request failed (${res.status})`);
  }

  return (await res.json()) as AnalysisResponse;
}
