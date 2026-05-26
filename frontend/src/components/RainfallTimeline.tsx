import { motion } from "framer-motion";
import { CloudRain } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
} from "recharts";
import type { RainfallPoint } from "../types";

/** 14-day rainfall trend — historical context for the flood prediction. */
export default function RainfallTimeline(
  { timeline }: { timeline: RainfallPoint[] },
) {
  if (!timeline?.length) return null;

  const data = timeline.map((p) => ({
    day: p.date.slice(5),               // MM-DD
    rain: Number(p.rainfall_mm.toFixed(1)),
  }));
  const total = data.reduce((s, d) => s + d.rain, 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      className="glass rounded-2xl p-6 shadow-card"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-bhoomi-cyan">
          <CloudRain size={18} />
          <h3 className="font-semibold text-slate-200">
            Rainfall Trend — last {data.length} days
          </h3>
        </div>
        <span className="text-xs text-slate-400">
          total <span className="text-bhoomi-cyan font-semibold">
            {total.toFixed(0)} mm</span>
        </span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="rainGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.55} />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(86,124,168,0.12)" />
          <XAxis dataKey="day" tick={{ fill: "#94a3b8", fontSize: 10 }} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }}
                 label={{ value: "mm", angle: -90, position: "insideLeft",
                          fill: "#64748b", fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: "#0e1626", border: "1px solid #334155",
              borderRadius: 10, color: "#e2e8f0" }}
            formatter={(v: number) => [`${v} mm`, "rainfall"]} />
          <Area type="monotone" dataKey="rain" stroke="#38bdf8"
                strokeWidth={2} fill="url(#rainGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  );
}
