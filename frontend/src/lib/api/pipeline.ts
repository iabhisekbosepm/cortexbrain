import { getDirectApiUrl, getStoredApiKey, api } from "@/lib/api-client";
import type { PipelineEvent, PipelineStatusResponse } from "@/lib/types";

export interface PipelineStreamCallbacks {
  onEvent: (event: PipelineEvent) => void;
  onHeartbeat: () => void;
  onError: (message: string) => void;
  onDisconnect: () => void;
}

export async function connectPipelineStream(
  callbacks: PipelineStreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  // Direct backend URL — bypass Next.js proxy which buffers SSE
  const baseUrl = getDirectApiUrl();
  const apiKey = getStoredApiKey();

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/pipeline/stream`, {
      method: "GET",
      headers: {
        ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
      },
      signal,
    });
  } catch (e) {
    if (signal?.aborted) return;
    callbacks.onError(e instanceof Error ? e.message : "Network error");
    callbacks.onDisconnect();
    return;
  }

  if (!response.ok) {
    const text = await response.text();
    callbacks.onError(`API Error ${response.status}: ${text}`);
    callbacks.onDisconnect();
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError("No response body");
    callbacks.onDisconnect();
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (!part.trim()) continue;

        let eventType = "";
        let dataStr = "";

        for (const line of part.split("\n")) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            dataStr = line.slice(6);
          }
        }

        if (!eventType || !dataStr) continue;

        try {
          const data = JSON.parse(dataStr);
          switch (eventType) {
            case "pipeline_event":
              callbacks.onEvent(data as PipelineEvent);
              break;
            case "heartbeat":
              callbacks.onHeartbeat();
              break;
            case "error":
              callbacks.onError(data.message || "Unknown error");
              break;
          }
        } catch {
          // Skip malformed JSON
        }
      }
    }
  } catch (e) {
    if (signal?.aborted) return;
    callbacks.onError(e instanceof Error ? e.message : "Stream error");
  }

  callbacks.onDisconnect();
}

export async function getPipelineStatus(): Promise<PipelineStatusResponse> {
  return api.get<PipelineStatusResponse>("/pipeline/status");
}
