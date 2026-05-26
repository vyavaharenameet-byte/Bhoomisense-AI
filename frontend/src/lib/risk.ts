// Shared risk-styling helpers so colours/labels are consistent everywhere.
import type { RiskLevel } from "../types";

export const RISK_COLOR: Record<RiskLevel, string> = {
  Low: "#34d399",
  Moderate: "#fbbf24",
  High: "#fb923c",
  Severe: "#f43f5e",
};

export function riskFromProbability(p: number): RiskLevel {
  if (p < 0.2) return "Low";
  if (p < 0.45) return "Moderate";
  if (p < 0.7) return "High";
  return "Severe";
}

export const pct = (n: number) => `${Math.round(n * 100)}%`;
