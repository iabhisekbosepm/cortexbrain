import { api } from "../api-client";
import type { ReviewQueueResponse, ReviewActionResponse } from "../types";

export async function getReviewQueue(): Promise<ReviewQueueResponse> {
  return api.get<ReviewQueueResponse>("/review/queue");
}

export async function approveNode(nodeId: string): Promise<ReviewActionResponse> {
  return api.post<ReviewActionResponse>(`/review/approve/${nodeId}`);
}

export async function rejectNode(nodeId: string): Promise<ReviewActionResponse> {
  return api.post<ReviewActionResponse>(`/review/reject/${nodeId}`);
}
