import { api } from "../api-client";
import type {
  DebugStatsResponse,
  SessionActivationsResponse,
  SalienceRecomputeResponse,
} from "../types";

export async function getDebugStats(): Promise<DebugStatsResponse> {
  return api.get<DebugStatsResponse>("/debug/stats");
}

export async function getSessionActivations(
  sessionId: string,
): Promise<SessionActivationsResponse> {
  return api.get<SessionActivationsResponse>(`/sessions/${sessionId}/activations`);
}

export async function recomputeSalience(): Promise<SalienceRecomputeResponse> {
  return api.post<SalienceRecomputeResponse>("/debug/salience-recompute");
}
