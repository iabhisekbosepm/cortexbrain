import { api } from "../api-client";
import type { WorkersStatusResponse } from "../types";

export async function getWorkersStatus(): Promise<WorkersStatusResponse> {
  return api.get<WorkersStatusResponse>("/workers/status");
}
