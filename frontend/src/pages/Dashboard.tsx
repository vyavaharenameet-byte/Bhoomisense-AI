import { motion, AnimatePresence } from "framer-motion";
import { Waves, Mountain, AlertTriangle, Star } from "lucide-react";
import type { PredictionResponse } from "../types";
import HazardCard from "../components/HazardCard";
import { SeverityGauge, FeatureGrid } from "../components/EnvironmentPanels";
import RiskMap from "../components/RiskMap";
import RainfallTimeline from "../components/RainfallTimeline";
import ExplainabilityPanel from "../components/ExplainabilityPanel";
import LoadingSkeleton from "../components/LoadingSkeleton";

interface Props {
  result: PredictionResponse | null;
  loading: boolean;
  error: string | null;
  onMapClick: (lat: number, lng: number) => void;
  isFavorite: boolean;
  onToggleFavorite: () => void;
}

/** Results dashboard — hazard gauges, map, environmental data, trends, XAI. */
export default function Dashboard({
  result, loading, error, onMapClick, isFavorite, onToggleFavorite,
}: Props) {
  if (loading) return <LoadingSkeleton />;

  if (error) {
    return (
      <div className="glass rounded-2xl p-8 text-center max-w-lg mx-auto">
        <AlertTriangle className="mx-auto text-bhoomi-rose mb-3" size={32} />
        <p className="text-slate-300">{error}</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="text-center text-slate-500 py-16">
        <motion.div animate={{ y: [0, -8, 0] }}
                    transition={{ repeat: Infinity, duration: 4 }}>
          <Waves className="mx-auto text-bhoomi-cyan/40" size={56} />
        </motion.div>
        <p className="mt-4">
          Search for an Indian city to generate a climate-risk assessment.
        </p>
      </div>
    );
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div key={result.location.name}
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        className="space-y-5"
      >
        {/* Location header + favorite */}
        <div className="text-center relative">
          <h2 className="text-2xl font-bold text-slate-100 inline-flex
                         items-center gap-2">
            {result.location.name}
            <button onClick={onToggleFavorite}
              title={isFavorite ? "Remove favorite" : "Save as favorite"}>
              <Star size={20}
                className={isFavorite
                  ? "fill-bhoomi-amber text-bhoomi-amber"
                  : "text-slate-500 hover:text-bhoomi-amber"} />
            </button>
          </h2>
          {result.location.country && (
            <p className="text-slate-500 text-sm">{result.location.country}</p>
          )}
        </div>

        {/* Three primary risk gauges */}
        <div className="grid sm:grid-cols-3 gap-5">
          <HazardCard title="Flood Risk" icon={<Waves size={18} />}
                      hazard={result.flood} delay={0} />
          <SeverityGauge score={result.severity_score}
                         level={result.severity_level} />
          <HazardCard title="Landslide Risk" icon={<Mountain size={18} />}
                      hazard={result.landslide} delay={0.15} />
        </div>

        {/* Map + environmental inputs */}
        <div className="grid lg:grid-cols-2 gap-5">
          <RiskMap result={result} onMapClick={onMapClick} />
          <FeatureGrid features={result.features} />
        </div>

        {/* Rainfall trend */}
        <RainfallTimeline timeline={result.rainfall_timeline} />

        {/* Explainable AI — per-hazard */}
        <ExplainabilityPanel
          explanation={result.explanation}
          floodFactors={result.flood_factors}
          landslideFactors={result.landslide_factors}
        />

        {/* Disclaimer */}
        <div className="glass rounded-xl p-4 border-bhoomi-amber/30
                        flex gap-3 items-start">
          <AlertTriangle className="text-bhoomi-amber shrink-0 mt-0.5" size={18} />
          <p className="text-xs text-slate-400">{result.disclaimer}</p>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
