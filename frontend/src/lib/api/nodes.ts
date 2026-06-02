import { api } from "../api-client";
import type { NodeDetailResponse, NodeHistoryResponse } from "../types";

export async function getNodeDetail(nodeId: string): Promise<NodeDetailResponse> {
  return api.get<NodeDetailResponse>(`/nodes/${nodeId}`);
}

export async function getNodeHistory(nodeId: string): Promise<NodeHistoryResponse> {
  return api.get<NodeHistoryResponse>(`/nodes/${nodeId}/history`);
}
