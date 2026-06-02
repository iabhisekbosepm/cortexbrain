import { api } from "../api-client";
import type { GraphOverviewResponse, GraphSubgraphResponse } from "../types";

export async function getGraphOverview(limit = 200): Promise<GraphOverviewResponse> {
  return api.get<GraphOverviewResponse>(`/graph/overview?limit=${limit}`);
}

export async function getGraphSubgraph(center: string, depth = 2): Promise<GraphSubgraphResponse> {
  return api.get<GraphSubgraphResponse>(`/graph/subgraph?center=${center}&depth=${depth}`);
}
