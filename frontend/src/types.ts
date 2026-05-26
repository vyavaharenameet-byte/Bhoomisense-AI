// types.ts — mirrors backend/app/schemas.py. Keep in sync with the API.

export interface GeoLocation {
  name: string;
  latitude: number;
  longitude: number;
  country: string | null;
}

export interface EnvironmentFeatures {
  elevation_m: number;
  slope_deg: number;
  rainfall_24h_mm: number;
  rainfall_7d_mm: number;
  rainfall_annual_mm: number;
  humidity_pct: number;
  temperature_c: number;
  pressure_hpa: number;
  soil_moisture: number;
  distance_to_river_km: number;
  river_discharge: number;
  water_level: number;
  vegetation_index: number;
  mining_proximity_km: number;
  drainage_density: number;
  urbanization: number;
  antecedent_precip_index: number;
  data_quality: Record<string, string>;
}

export type RiskLevel = "Low" | "Moderate" | "High" | "Severe";

export interface HazardResult {
  probability: number;
  risk_level: RiskLevel;
  confidence: number;
  contributing_factors: string[];
}

export interface FeatureContribution {
  feature: string;
  importance: number;
}

export interface RainfallPoint {
  date: string;
  rainfall_mm: number;
}

export interface PredictionResponse {
  location: GeoLocation;
  features: EnvironmentFeatures;
  flood: HazardResult;
  landslide: HazardResult;
  severity_score: number;
  severity_level: RiskLevel;
  explanation: string;
  flood_factors: FeatureContribution[];
  landslide_factors: FeatureContribution[];
  rainfall_timeline: RainfallPoint[];
  disclaimer: string;
}
