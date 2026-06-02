import { api } from "../api-client";
import type { DatasetsResponse, DatasetDataResponse, DataItemContentResponse } from "../types";

export async function getDatasets(name?: string): Promise<DatasetsResponse> {
  const params = name ? `?name=${encodeURIComponent(name)}` : "";
  return api.get<DatasetsResponse>(`/datasets${params}`);
}

export async function getDatasetData(datasetName: string): Promise<DatasetDataResponse> {
  return api.get<DatasetDataResponse>(`/datasets/${encodeURIComponent(datasetName)}/data`);
}

export async function getDataItemContent(dataId: string, maxChars: number = 50000): Promise<DataItemContentResponse> {
  return api.get<DataItemContentResponse>(`/data/${encodeURIComponent(dataId)}/content?max_chars=${maxChars}`);
}
