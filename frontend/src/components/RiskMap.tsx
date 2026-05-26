import { MapContainer, TileLayer, CircleMarker, Popup, useMapEvents } from "react-leaflet";
import type { PredictionResponse } from "../types";
import { RISK_COLOR } from "../lib/risk";

interface Props {
  result: PredictionResponse;
  onMapClick: (lat: number, lng: number) => void;
}

/** Captures map clicks so users can probe any point, not just searched cities. */
function ClickHandler({ onMapClick }: { onMapClick: Props["onMapClick"] }) {
  useMapEvents({
    click: (e) => onMapClick(e.latlng.lat, e.latlng.lng),
  });
  return null;
}

/**
 * Interactive GIS map. The marker is sized + coloured by severity, acting as a
 * single-point "risk heatmap". To build a true multi-cell heatmap, query
 * /api/predict/coords over a lat/lon grid and render a leaflet.heat layer —
 * see ARCHITECTURE.md § "Risk heatmap".
 */
export default function RiskMap({ result, onMapClick }: Props) {
  const { latitude, longitude } = result.location;
  const color = RISK_COLOR[result.severity_level];

  return (
    <div className="glass rounded-2xl p-2 shadow-card overflow-hidden">
      <MapContainer
        center={[latitude, longitude]}
        zoom={11}
        style={{ height: 360, borderRadius: 14 }}
        key={`${latitude}-${longitude}`}  // re-centre on new location
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ClickHandler onMapClick={onMapClick} />
        {/* Outer glow ring scaled by severity */}
        <CircleMarker
          center={[latitude, longitude]}
          radius={18 + result.severity_score / 4}
          pathOptions={{ color, fillColor: color, fillOpacity: 0.15, weight: 1 }}
        />
        <CircleMarker
          center={[latitude, longitude]}
          radius={9}
          pathOptions={{ color, fillColor: color, fillOpacity: 0.9, weight: 2 }}
        >
          <Popup>
            <strong>{result.location.name}</strong>
            <br />
            Severity {result.severity_score.toFixed(0)}/100 ·{" "}
            {result.severity_level}
          </Popup>
        </CircleMarker>
      </MapContainer>
      <p className="text-xs text-slate-500 px-2 py-1.5">
        Tip: click anywhere on the map to analyze that point.
      </p>
    </div>
  );
}
