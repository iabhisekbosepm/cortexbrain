import { api } from "../api-client";
import type { HealthResponse } from "../types";

export async function getHealth(): Promise<HealthResponse> {
  return api.get<HealthResponse>("/health");
}
