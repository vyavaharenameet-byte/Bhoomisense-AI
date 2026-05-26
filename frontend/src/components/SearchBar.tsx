import { useState } from "react";
import { motion } from "framer-motion";
import { Search, MapPin, Loader2 } from "lucide-react";

interface Props {
  onSearch: (city: string) => void;
  loading: boolean;
  history: string[];
}

/** Hero search input + recent-search chips. */
export default function SearchBar({ onSearch, loading, history }: Props) {
  const [value, setValue] = useState("");

  const submit = () => {
    const city = value.trim();
    if (city && !loading) onSearch(city);
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-1.5 flex items-center gap-2 shadow-card"
      >
        <MapPin className="ml-3 text-bhoomi-cyan shrink-0" size={20} />
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Enter a city or location — e.g. Mumbai, Wayanad…"
          className="flex-1 bg-transparent outline-none py-3 text-slate-100
                     placeholder:text-slate-500"
        />
        <button
          onClick={submit}
          disabled={loading}
          className="flex items-center gap-2 rounded-xl bg-bhoomi-cyan/90
                     hover:bg-bhoomi-cyan text-slate-900 font-semibold
                     px-5 py-2.5 transition disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="animate-spin" size={18} />
          ) : (
            <Search size={18} />
          )}
          {loading ? "Analyzing" : "Analyze"}
        </button>
      </motion.div>

      {history.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3 justify-center">
          <span className="text-xs text-slate-500 self-center">Recent:</span>
          {history.map((c) => (
            <button
              key={c}
              onClick={() => !loading && onSearch(c)}
              className="text-xs px-3 py-1 rounded-full glass
                         hover:border-bhoomi-cyan/50 text-slate-300 transition"
            >
              {c}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
