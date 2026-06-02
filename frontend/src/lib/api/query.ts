import { api } from "../api-client";
import type { QueryRequest, QueryResponse } from "../types";

export async function submitQuery(req: QueryRequest): Promise<QueryResponse> {
  return api.post<QueryResponse>("/query", req);
}
