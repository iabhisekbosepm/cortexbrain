import { api } from "../api-client";
import type { DashboardStatsResponse } from "../types";

export async function getDashboardStats(): Promise<DashboardStatsResponse> {
  return api.get<DashboardStatsResponse>("/dashboard/stats");
}
