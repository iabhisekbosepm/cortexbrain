"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { QueryInput } from "@/components/query/query-input";
import { QueryHistory } from "@/components/query/query-history";
import { QueryDetailPanel } from "@/components/query/query-detail-panel";
import { ThinkingTrace } from "@/components/query/thinking-trace";
import { useSession } from "@/hooks/use-session";
import { useToast } from "@/components/ui/toast";
import { submitAgentQuery } from "@/lib/api/agent-query";
import { generateId } from "@/lib/utils";
import { submitQuery } from "@/lib/api/query";
import { getStoredUserId } from "@/lib/api-client";
import type { QueryHistoryEntry, AgentStep, ConversationMessage, QueryMode } from "@/lib/types";

const MODE_STORAGE_KEY = "cortexbrain_query_mode";

export default function QueryPage() {
  const { sessionId, newSession } = useSession();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<QueryHistoryEntry[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Query mode (persisted in localStorage)
  const [queryMode, setQueryMode] = useState<QueryMode>("agent");
  useEffect(() => {
    const saved = localStorage.getItem(MODE_STORAGE_KEY) as QueryMode | null;
    if (saved === "agent" || saved === "normal") setQueryMode(saved);
  }, []);
  function handleModeChange(mode: QueryMode) {
    setQueryMode(mode);
    localStorage.setItem(MODE_STORAGE_KEY, mode);
  }

  // Streaming state (agent mode only)
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingSteps, setStreamingSteps] = useState<AgentStep[]>([]);
  const [streamingQuery, setStreamingQuery] = useState<string | null>(null);
  const stepsRef = useRef<AgentStep[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const selectedEntry = history.find((e) => e.id === selectedId) || null;

  // Build conversation history from past entries
  const buildConversationHistory = useCallback((): ConversationMessage[] => {
    const messages: ConversationMessage[] = [];
    const entries = [...history].reverse();
    for (const entry of entries) {
      messages.push({ role: "user", content: entry.query });
      messages.push({ role: "assistant", content: entry.answer });
    }
    return messages.slice(-20);
  }, [history]);

  // --- Agent mode submit ---
  async function handleAgentSubmit(query: string) {
    setLoading(true);
    setIsStreaming(true);
    setStreamingSteps([]);
    setStreamingQuery(query);
    stepsRef.current = [];

    const controller = new AbortController();
    abortRef.current = controller;

    const conversationHistory = buildConversationHistory();

    await submitAgentQuery(
      {
        query,
        session_id: sessionId,
        user_id: getStoredUserId(),
        conversation_history: conversationHistory,
      },
      {
        onStep: (step) => {
          stepsRef.current = [...stepsRef.current, step];
          setStreamingSteps([...stepsRef.current]);
        },
        onAnswer: (res) => {
          const entry: QueryHistoryEntry = {
            id: generateId(),
            query,
            answer: res.answer,
            confidence: (res.confidence as QueryHistoryEntry["confidence"]) || "medium",
            confidence_score: res.confidence_score,
            sources: res.sources.map((s) => ({
              node_id: s.node_id,
              source_name: s.source_name,
              confidence: s.confidence,
              activation_score: s.activation_score,
            })),
            tokens_used: { input: 0, output: 0 },
            fallback: res.fallback,
            auto_learned: res.auto_learned,
            timestamp: new Date(),
            session_id: res.session_id,
            steps: stepsRef.current,
            mode: "agent",
          };
          setHistory((prev) => [entry, ...prev]);
          setSelectedId(entry.id);
        },
        onError: (message) => {
          toast(message, "error");
        },
        onDone: () => {
          setLoading(false);
          setIsStreaming(false);
          setStreamingQuery(null);
          setStreamingSteps([]);
          stepsRef.current = [];
          abortRef.current = null;
        },
      },
      controller.signal,
    );
  }

  // --- Normal mode submit ---
  async function handleNormalSubmit(query: string) {
    setLoading(true);
    setStreamingQuery(query);

    try {
      const res = await submitQuery({
        query,
        session_id: sessionId,
        user_id: getStoredUserId(),
      });

      const entry: QueryHistoryEntry = {
        id: generateId(),
        query,
        answer: res.answer,
        confidence: res.confidence,
        confidence_score: res.confidence_score,
        sources: res.sources,
        tokens_used: res.tokens_used,
        fallback: res.fallback,
        auto_learned: res.auto_learned,
        insights: res.insights,
        images: res.images,
        timestamp: new Date(),
        session_id: res.session_id,
        mode: "normal",
      };
      setHistory((prev) => [entry, ...prev]);
      setSelectedId(entry.id);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Query failed", "error");
    } finally {
      setLoading(false);
      setStreamingQuery(null);
    }
  }

  // --- Route to the right handler ---
  function handleSubmit(query: string) {
    if (queryMode === "agent") {
      handleAgentSubmit(query);
    } else {
      handleNormalSubmit(query);
    }
  }

  function handleCancel() {
    abortRef.current?.abort();
    setLoading(false);
    setIsStreaming(false);
    setStreamingQuery(null);
    setStreamingSteps([]);
    stepsRef.current = [];
    abortRef.current = null;
  }

  function handleNewSession() {
    if (isStreaming) handleCancel();
    newSession();
    setHistory([]);
    setSelectedId(null);
    toast("New session started", "info");
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header bar */}
        <div className="px-6 py-3 border-b border-gray-200 bg-white shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Query</h2>
              <p className="text-xs text-gray-500">
                {queryMode === "agent"
                  ? "Agent mode — multi-step reasoning with tool calls"
                  : "Normal mode — fast single-pass response"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {queryMode === "agent" ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-copper-50 border border-copper-200 px-2.5 py-0.5 text-[11px] font-medium text-copper-700">
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                  </svg>
                  Agent Mode
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-200 px-2.5 py-0.5 text-[11px] font-medium text-blue-700">
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                  </svg>
                  Normal Mode
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* Streaming indicator — Agent mode: ThinkingTrace, Normal mode: simple loader */}
          {loading && streamingQuery && (
            <div className="space-y-3 mb-4">
              {/* User question */}
              <div className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl rounded-br-md bg-copper-600 px-4 py-2.5 text-sm text-white">
                  {streamingQuery}
                </div>
              </div>

              {/* Loading state */}
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-2xl rounded-bl-md px-4 py-3 bg-white border border-copper-200">
                  {isStreaming ? (
                    <>
                      <ThinkingTrace steps={streamingSteps} isStreaming={true} />
                      <button
                        onClick={handleCancel}
                        className="mt-2 text-[11px] text-gray-400 hover:text-red-500 transition-colors"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <div className="flex items-center gap-2 py-1">
                      <svg className="h-4 w-4 animate-spin text-copper-600" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      <span className="text-sm text-gray-500">Querying knowledge base...</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          <QueryHistory
            history={history}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>

        {/* Input area pinned to bottom */}
        <div className="px-6 py-4 border-t border-gray-200 bg-white shrink-0">
          <QueryInput
            onSubmit={handleSubmit}
            loading={loading}
            sessionId={sessionId}
            onNewSession={handleNewSession}
            mode={queryMode}
            onModeChange={handleModeChange}
          />
        </div>
      </div>

      {/* Right: Detail panel */}
      {selectedEntry && (
        <div className="w-96 border-l border-gray-200 bg-white shrink-0 hidden lg:flex flex-col">
          <QueryDetailPanel
            entry={selectedEntry}
            onClose={() => setSelectedId(null)}
          />
        </div>
      )}
    </div>
  );
}
