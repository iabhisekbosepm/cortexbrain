import { api } from "../api-client";
import type { CorrectionRequest, CorrectionResponse } from "../types";

export async function submitCorrection(req: CorrectionRequest): Promise<CorrectionResponse> {
  return api.post<CorrectionResponse>("/correct", req);
}
