import { api } from "@/lib/api-client";
import type { TimelineResponse } from "@/lib/types";

export interface TimelineParams {
  action?: string;
  start?: string;
  end?: string;
  limit?: number;
  offset?: number;
}

export async function getTimeline(params: TimelineParams = {}): Promise<TimelineResponse> {
  const searchParams = new URLSearchParams();
  if (params.action) searchParams.set("action", params.action);
  if (params.start) searchParams.set("start", params.start);
  if (params.end) searchParams.set("end", params.end);
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.offset) searchParams.set("offset", String(params.offset));

  const qs = searchParams.toString();
  return api.get<TimelineResponse>(`/timeline${qs ? `?${qs}` : ""}`);
}
