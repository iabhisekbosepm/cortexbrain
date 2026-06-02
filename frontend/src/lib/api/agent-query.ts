import { getDirectApiUrl, getStoredApiKey } from "@/lib/api-client";
import type { AgentStep, AgentAnswerEvent, ConversationMessage } from "@/lib/types";

export interface AgentQueryCallbacks {
  onStep: (step: AgentStep) => void;
  onAnswer: (answer: AgentAnswerEvent) => void;
  onError: (message: string) => void;
  onDone: () => void;
}

export async function submitAgentQuery(
  req: {
    query: string;
    session_id?: string;
    user_id: string;
    conversation_history: ConversationMessage[];
  },
  callbacks: AgentQueryCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  // Use direct backend URL — Next.js proxy buffers SSE, breaking real-time streaming
  const baseUrl = getDirectApiUrl();
  const apiKey = getStoredApiKey();

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/query/agent`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
      },
      body: JSON.stringify(req),
      signal,
    });
  } catch (e) {
    if (signal?.aborted) return;
    callbacks.onError(e instanceof Error ? e.message : "Network error");
    callbacks.onDone();
    return;
  }

  if (!response.ok) {
    const text = await response.text();
    callbacks.onError(`API Error ${response.status}: ${text}`);
    callbacks.onDone();
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError("No response body");
    callbacks.onDone();
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages (separated by double newlines)
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
            case "step":
              callbacks.onStep({ ...data, timestamp: new Date() });
              break;
            case "answer":
              callbacks.onAnswer(data);
              break;
            case "error":
              callbacks.onError(data.message || "Unknown error");
              break;
            case "done":
              callbacks.onDone();
              return;
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

  callbacks.onDone();
}
