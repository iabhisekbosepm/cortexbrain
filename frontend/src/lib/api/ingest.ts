import { api } from "../api-client";
import type {
  IngestResponse,
  BatchIngestResponse,
  BatchStatusResponse,
  TextIngestResponse,
  TextIngestAsyncResponse,
} from "../types";

export async function ingestSync(
  files: File[],
  datasetName = "default",
  sourceType = "document",
): Promise<IngestResponse> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  form.append("dataset_name", datasetName);
  form.append("source_type", sourceType);
  return api.postForm<IngestResponse>("/ingest", form);
}

export async function ingestBatch(
  files: File[],
  datasetName = "default",
): Promise<BatchIngestResponse> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  form.append("dataset_name", datasetName);
  return api.postForm<BatchIngestResponse>("/ingest/batch", form);
}

export async function getBatchStatus(taskId: string): Promise<BatchStatusResponse> {
  return api.get<BatchStatusResponse>(`/ingest/batch/${taskId}`);
}

export async function ingestText(
  text: string,
  datasetName = "default",
  sourceType = "text",
): Promise<TextIngestResponse> {
  return api.post<TextIngestResponse>("/ingest/text", {
    text,
    dataset_name: datasetName,
    source_type: sourceType,
  });
}

export async function ingestTextAsync(
  text: string,
  datasetName = "default",
): Promise<TextIngestAsyncResponse> {
  return api.post<TextIngestAsyncResponse>("/ingest/text/async", {
    text,
    dataset_name: datasetName,
  });
}
