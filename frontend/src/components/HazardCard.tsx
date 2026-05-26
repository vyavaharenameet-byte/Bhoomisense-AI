import { motion } from "framer-motion";
import type { HazardResult } from "../types";
import { RISK_COLOR, pct } from "../lib/risk";

interface Props {
  title: string;
  icon: React.ReactNode;
  hazard: HazardResult;
  delay?: number;
}

/** Glass card: animated radial gauge + the model's contributing factors. */
export default function HazardCard({ title, icon, hazard, delay = 0 }: Props) {
  const color = RISK_COLOR[hazard.risk_level];
  const R = 52;
  const C = 2 * Math.PI * R;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5 }}
      className="glass rounded-2xl p-6 flex flex-col items-center shadow-card"
    >
      <div className="flex items-center gap-2 text-slate-300 mb-4">
        <span style={{ color }}>{icon}</span>
        <h3 className="font-semibold">{title}</h3>
      </div>

      <div className="relative w-32 h-32">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 128 128">
          <circle cx="64" cy="64" r={R} fill="none"
                  stroke="rgba(86,124,168,0.18)" strokeWidth="10" />
          <motion.circle
            cx="64" cy="64" r={R} fill="none" stroke={color}
            strokeWidth="10" strokeLinecap="round" strokeDasharray={C}
            initial={{ strokeDashoffset: C }}
            animate={{ strokeDashoffset: C * (1 - hazard.probability) }}
            transition={{ delay: delay + 0.2, duration: 1, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold" style={{ color }}>
            {pct(hazard.probability)}
          </span>
          <span className="text-[10px] text-slate-400">probability</span>
        </div>
      </div>

      <div className="mt-3 px-3 py-1 rounded-full text-sm font-semibold"
           style={{ background: `${color}22`, color }}>
        {hazard.risk_level} Risk
      </div>
      <p className="text-[11px] text-slate-500 mt-1">
        Confidence {pct(hazard.confidence)}
      </p>

      {/* Contributing factors */}
      <ul className="mt-3 w-full space-y-1">
        {hazard.contributing_factors.slice(0, 4).map((f, i) => (
          <motion.li
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: delay + 0.4 + i * 0.08 }}
            className="text-[11px] text-slate-400 flex items-start gap-1.5"
          >
            <span className="mt-1 w-1 h-1 rounded-full shrink-0"
                  style={{ background: color }} />
            {f}
          </motion.li>
        ))}
      </ul>
    </motion.div>
  );
}
