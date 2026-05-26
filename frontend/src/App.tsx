import { useState } from "react";
import { motion } from "framer-motion";
import { Globe2, Star } from "lucide-react";
import {
  api, loadHistory, pushHistory, loadFavorites, toggleFavorite,
} from "./api";
import type { PredictionResponse } from "./types";
import SearchBar from "./components/SearchBar";
import Dashboard from "./pages/Dashboard";

/**
 * BhoomiSense AI — root component.
 * Holds the prediction-result state and orchestrates city / map-click lookups,
 * search history and favorites. Routing, auth and the admin dashboard are
 * deliberately omitted here — see ARCHITECTURE.md § "Roadmap".
 */
export default function App() {
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>(loadHistory());
  const [favorites, setFavorites] = useState<string[]>(loadFavorites());

  async function runCity(city: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await api.predictByCity(city);
      setResult(data);
      setHistory(pushHistory(data.location.name));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function runCoords(lat: number, lng: number) {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.predictByCoords(lat, lng));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  const currentName = result?.location.name ?? "";
  const isFavorite = favorites.includes(currentName);

  return (
    <div className="bhoomi-bg min-h-screen">
      {/* Header */}
      <header className="border-b border-bhoomi-border">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-3">
          <motion.div animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 28, ease: "linear" }}>
            <Globe2 className="text-bhoomi-cyan" size={26} />
          </motion.div>
          <div>
            <h1 className="font-bold text-lg leading-tight">
              BhoomiSense<span className="text-bhoomi-cyan"> AI</span>
            </h1>
            <p className="text-[11px] text-slate-500 -mt-0.5">
            AI-powered climate intelligence platform
            </p>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        <section className="text-center space-y-3">
          <motion.h2 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Predict . Prevent .
            <br />
            <span className="bg-gradient-to-r from-bhoomi-cyan to-bhoomi-teal
                             bg-clip-text text-transparent">
              Protect !
            </span>
          </motion.h2>
          <p className="text-slate-400 max-w-xl mx-auto text-sm">
          Advanced disaster intelligence platform for flood and landslide 
          risk monitoring across India.
          </p>
        </section>

        <SearchBar onSearch={runCity} loading={loading} history={history} />

        {/* Favorites */}
        {favorites.length > 0 && (
          <div className="flex flex-wrap gap-2 justify-center -mt-3">
            <span className="text-xs text-slate-500 self-center flex
                             items-center gap-1">
              <Star size={12} className="fill-bhoomi-amber text-bhoomi-amber" />
              Favorites:
            </span>
            {favorites.map((c) => (
              <button key={c} onClick={() => !loading && runCity(c)}
                className="text-xs px-3 py-1 rounded-full glass
                           hover:border-bhoomi-amber/50 text-slate-300 transition">
                {c}
              </button>
            ))}
          </div>
        )}

        <Dashboard
          result={result} loading={loading} error={error}
          onMapClick={runCoords}
          isFavorite={isFavorite}
          onToggleFavorite={() => currentName &&
            setFavorites(toggleFavorite(currentName))}
        />
      </main>

      {/* Footer */}
      <footer className="border-t border-bhoomi-border mt-12">
        <div className="max-w-6xl mx-auto px-4 py-5 text-xs text-slate-600
                        flex flex-wrap gap-2 justify-between">
          <span>Environmental Intelligence, Reimagined.</span>
        </div>
      </footer>
    </div>
  );
}
