import { api } from "./client";

export interface HealthResponse {
  status: "ok" | "degraded";
  service: string;
  version: string;
  checks: Record<string, string>;
  timestamp: string;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health/");
  return data;
}
