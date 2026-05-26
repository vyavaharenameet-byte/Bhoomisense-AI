import { motion } from "framer-motion";
import {
  Mountain, CloudRain, Droplets, Thermometer, Wind, Waves,
  TreePine, Building2, Gauge, Pickaxe, Activity,
} from "lucide-react";
import type { EnvironmentFeatures, RiskLevel } from "../types";
import { RISK_COLOR } from "../lib/risk";

/** Big animated composite-severity gauge. */
export function SeverityGauge({
  score, level,
}: { score: number; level: RiskLevel }) {
  const color = RISK_COLOR[level];
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass rounded-2xl p-6 shadow-card flex flex-col
                 items-center justify-center"
    >
      <h3 className="text-slate-300 font-semibold mb-1">
        Environmental Severity
      </h3>
      <p className="text-xs text-slate-500 mb-3">composite hazard index</p>
      <div className="relative">
        <motion.div className="text-6xl font-extrabold" style={{ color }}
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          {score.toFixed(0)}
        </motion.div>
        <span className="absolute -right-7 top-2 text-slate-500 text-sm">
          /100
        </span>
      </div>
      <div className="w-full h-2 rounded-full bg-slate-700/40 mt-4 overflow-hidden">
        <motion.div className="h-full rounded-full" style={{ background: color }}
                    initial={{ width: 0 }} animate={{ width: `${score}%` }}
                    transition={{ duration: 1, ease: "easeOut" }} />
      </div>
      <span className="mt-3 font-semibold" style={{ color }}>
        {level} Severity
      </span>
    </motion.div>
  );
}

const FEATURE_META: Record<string, { icon: React.ReactNode; label: string;
  fmt: (n: number) => string }> = {
  elevation_m: { icon: <Mountain size={16} />, label: "Elevation",
    fmt: (n) => `${n.toFixed(0)} m` },
  slope_deg: { icon: <Mountain size={16} />, label: "Slope",
    fmt: (n) => `${n.toFixed(1)}°` },
  rainfall_24h_mm: { icon: <CloudRain size={16} />, label: "Rain (24h)",
    fmt: (n) => `${n.toFixed(0)} mm` },
  rainfall_7d_mm: { icon: <CloudRain size={16} />, label: "Rain (7d)",
    fmt: (n) => `${n.toFixed(0)} mm` },
  soil_moisture: { icon: <Droplets size={16} />, label: "Soil moisture",
    fmt: (n) => `${(n * 100).toFixed(0)}%` },
  river_discharge: { icon: <Activity size={16} />, label: "River discharge",
    fmt: (n) => `${n.toFixed(0)} m³/s` },
  water_level: { icon: <Waves size={16} />, label: "Water level",
    fmt: (n) => `${n.toFixed(1)} m` },
  distance_to_river_km: { icon: <Waves size={16} />, label: "River distance",
    fmt: (n) => `${n.toFixed(1)} km` },
  mining_proximity_km: { icon: <Pickaxe size={16} />, label: "Mining proximity",
    fmt: (n) => `${n.toFixed(1)} km` },
  vegetation_index: { icon: <TreePine size={16} />, label: "Vegetation (NDVI)",
    fmt: (n) => n.toFixed(2) },
  humidity_pct: { icon: <Droplets size={16} />, label: "Humidity",
    fmt: (n) => `${n.toFixed(0)}%` },
  temperature_c: { icon: <Thermometer size={16} />, label: "Temperature",
    fmt: (n) => `${n.toFixed(1)}°C` },
  pressure_hpa: { icon: <Wind size={16} />, label: "Pressure",
    fmt: (n) => `${n.toFixed(0)} hPa` },
  urbanization: { icon: <Building2 size={16} />, label: "Urbanization",
    fmt: (n) => `${(n * 100).toFixed(0)}%` },
  antecedent_precip_index: { icon: <Gauge size={16} />, label: "Saturation idx",
    fmt: (n) => n.toFixed(2) },
};

const ALWAYS_ESTIMATED = ["vegetation_index", "urbanization", "water_level"];

/** Grid of the environmental + geospatial inputs the models used. */
export function FeatureGrid({ features }: { features: EnvironmentFeatures }) {
  return (
    <div className="glass rounded-2xl p-6 shadow-card">
      <h3 className="text-slate-300 font-semibold mb-1">
        Environmental &amp; Geospatial Inputs
      </h3>
      <p className="text-xs text-slate-500 mb-4">
        Live data for this location ·{" "}
        <span className="text-bhoomi-teal">measured</span> vs{" "}
        <span className="text-bhoomi-amber">estimated</span>
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {Object.entries(FEATURE_META).map(([key, meta], i) => {
          const value = features[key as keyof EnvironmentFeatures] as number;
          const dqKey = key === "distance_to_river_km" ? "distance_to_river"
            : key === "mining_proximity_km" ? "mining_proximity" : key;
          const estimated = features.data_quality?.[dqKey] === "estimated"
            || ALWAYS_ESTIMATED.includes(key);
          return (
            <motion.div key={key}
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.04 * i }}
              className="rounded-xl bg-slate-800/40 p-3 border border-bhoomi-border"
            >
              <div className="flex items-center gap-1.5 text-slate-400 text-xs">
                <span className="text-bhoomi-cyan">{meta.icon}</span>
                {meta.label}
                <span className={`ml-auto w-1.5 h-1.5 rounded-full ${
                  estimated ? "bg-bhoomi-amber" : "bg-bhoomi-teal"}`}
                  title={estimated ? "estimated" : "measured"} />
              </div>
              <div className="text-lg font-semibold text-slate-100 mt-1">
                {meta.fmt(value)}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
