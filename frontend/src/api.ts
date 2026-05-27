// api.ts — typed client for the BhoomiSense backend.
import type { PredictionResponse } from "./types";

// In dev, Vite proxies /api -> localhost:8000. In production set VITE_API_URL.
const BASE = import.meta.env.VITE_API_URL ?? "";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  predictByCity: (city: string) =>
    post<PredictionResponse>("/api/predict/city/", { city }),
  predictByCoords: (latitude: number, longitude: number) =>
    post<PredictionResponse>("/api/predict/coords/", { latitude, longitude }),
  modelMetadata: async () => {
    const res = await fetch(`${BASE}/api/model/metadata`);
    return res.json();
  },
};

// --- Local persistence (stand-in for the DB-backed history/favorites) ------
// NOTE: when you add user auth + Postgres, replace these with server calls.
function read(key: string): string[] {
  try {
    return JSON.parse(localStorage.getItem(key) ?? "[]");
  } catch {
    return [];
  }
}

export function loadHistory(): string[] {
  return read("bhoomi_history");
}
export function pushHistory(city: string): string[] {
  const next = [city, ...loadHistory().filter((c) => c !== city)].slice(0, 8);
  localStorage.setItem("bhoomi_history", JSON.stringify(next));
  return next;
}

export function loadFavorites(): string[] {
  return read("bhoomi_favorites");
}
export function toggleFavorite(city: string): string[] {
  const cur = loadFavorites();
  const next = cur.includes(city)
    ? cur.filter((c) => c !== city)
    : [city, ...cur].slice(0, 12);
  localStorage.setItem("bhoomi_favorites", JSON.stringify(next));
  return next;
}
