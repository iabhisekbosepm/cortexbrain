"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { QueryMode } from "@/lib/types";

interface QueryInputProps {
  onSubmit: (query: string) => void;
  loading: boolean;
  sessionId: string;
  onNewSession: () => void;
  mode: QueryMode;
  onModeChange: (mode: QueryMode) => void;
}

export function QueryInput({ onSubmit, loading, sessionId, onNewSession, mode, onModeChange }: QueryInputProps) {
  const [query, setQuery] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    onSubmit(trimmed);
    setQuery("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="font-mono bg-gray-100 px-2 py-0.5 rounded">{sessionId.slice(0, 8)}...</span>
          <button type="button" onClick={onNewSession} className="text-copper-600 hover:text-copper-700">
            New Session
          </button>
        </div>

        {/* Mode toggle */}
        <div className="flex items-center rounded-lg border border-gray-200 bg-gray-50 p-0.5">
          <button
            type="button"
            onClick={() => onModeChange("normal")}
            disabled={loading}
            className={cn(
              "flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium transition-all",
              mode === "normal"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700",
            )}
          >
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
            Normal
          </button>
          <button
            type="button"
            onClick={() => onModeChange("agent")}
            disabled={loading}
            className={cn(
              "flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium transition-all",
              mode === "agent"
                ? "bg-copper-600 text-white shadow-sm"
                : "text-gray-500 hover:text-gray-700",
            )}
          >
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
            Agent
          </button>
        </div>
      </div>

      <div className="relative">
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={mode === "agent" ? "Ask CortexBrain — agent will search, reason, and answer..." : "Ask CortexBrain a question..."}
          rows={3}
          className="block w-full rounded-xl border border-gray-300 px-4 py-3 pr-24 text-sm shadow-sm placeholder:text-gray-400 focus:border-copper-500 focus:outline-none focus:ring-1 focus:ring-copper-500 resize-none"
        />
        <div className="absolute bottom-3 right-3">
          <Button type="submit" loading={loading} className="rounded-lg">
            Send
          </Button>
        </div>
      </div>
      <p className="text-xs text-gray-400">Press Enter to send, Shift+Enter for new line</p>
    </form>
  );
}
