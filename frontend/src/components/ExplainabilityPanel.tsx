import { useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, BarChart3 } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip,
} from "recharts";
import type { FeatureContribution } from "../types";

interface Props {
  explanation: string;
  floodFactors: FeatureContribution[];
  landslideFactors: FeatureContribution[];
}

/**
 * Explainable-AI dashboard. Each hazard has its OWN trained model with its own
 * feature set, so the SHAP importances are shown per hazard via a toggle.
 */
export default function ExplainabilityPanel(
  { explanation, floodFactors, landslideFactors }: Props,
) {
  const [hazard, setHazard] = useState<"flood" | "landslide">("flood");
  const factors = hazard === "flood" ? floodFactors : landslideFactors;
  const data = factors.map((f) => ({
    name: f.feature, value: Math.round(f.importance * 100),
  }));

  return (
    <div className="grid lg:grid-cols-2 gap-5">
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-6 shadow-card"
      >
        <div className="flex items-center gap-2 text-bhoomi-teal mb-3">
          <Sparkles size={18} />
          <h3 className="font-semibold text-slate-200">AI Risk Explanation</h3>
        </div>
        <p className="text-slate-300 leading-relaxed text-sm">{explanation}</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass rounded-2xl p-6 shadow-card"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-bhoomi-cyan">
            <BarChart3 size={18} />
            <h3 className="font-semibold text-slate-200">
              Feature Importance (SHAP)
            </h3>
          </div>
          <div className="flex gap-1 text-xs">
            {(["flood", "landslide"] as const).map((h) => (
              <button key={h} onClick={() => setHazard(h)}
                className={`px-2.5 py-1 rounded-lg capitalize transition ${
                  hazard === h
                    ? "bg-bhoomi-cyan/90 text-slate-900 font-semibold"
                    : "glass text-slate-400"}`}>
                {h}
              </button>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={210}>
          <BarChart data={data} layout="vertical"
                    margin={{ left: 10, right: 20 }}>
            <XAxis type="number" hide />
            <YAxis dataKey="name" type="category" width={140}
                   tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Tooltip cursor={{ fill: "rgba(56,189,248,0.08)" }}
              contentStyle={{ background: "#0e1626", border: "1px solid #334155",
                borderRadius: 10, color: "#e2e8f0" }}
              formatter={(v: number) => [`${v}%`, "importance"]} />
            <Bar dataKey="value" radius={[0, 6, 6, 0]}>
              {data.map((_, i) => (
                <Cell key={i} fill={`rgba(56,189,248,${0.95 - i * 0.12})`} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </motion.div>
    </div>
  );
}
