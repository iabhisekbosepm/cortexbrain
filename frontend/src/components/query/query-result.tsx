"use client";

import ReactMarkdown from "react-markdown";
import { ConfidenceBadge } from "@/components/ui/badge";
import { ThinkingTrace } from "@/components/query/thinking-trace";
import { cn } from "@/lib/utils";
import type { QueryHistoryEntry } from "@/lib/types";

interface QueryResultProps {
  entry: QueryHistoryEntry;
  selected: boolean;
  onSelect: () => void;
}

export function QueryResult({ entry, selected, onSelect }: QueryResultProps) {
  return (
    <div className="space-y-3">
      {/* User question */}
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-copper-600 px-4 py-2.5 text-sm text-white">
          {entry.query}
        </div>
      </div>

      {/* Thinking trace (if agent mode) */}
      {entry.steps && entry.steps.length > 0 && (
        <div className="flex justify-start">
          <div className="max-w-[85%] px-4 py-1">
            <ThinkingTrace steps={entry.steps} isStreaming={false} />
          </div>
        </div>
      )}

      {/* AI answer — click to show details in side panel */}
      <div className="flex justify-start">
        <button
          onClick={onSelect}
          className={cn(
            "max-w-[85%] text-left rounded-2xl rounded-bl-md px-4 py-3 text-sm transition-colors border",
            selected
              ? "bg-copper-50 border-copper-200"
              : "bg-white border-gray-200 hover:border-gray-300",
          )}
        >
          <div className="text-gray-800 leading-relaxed prose prose-sm prose-gray max-w-none prose-p:my-1.5 prose-ul:my-1.5 prose-li:my-0.5 prose-headings:my-2 prose-strong:text-gray-900">
            <ReactMarkdown>{entry.answer}</ReactMarkdown>
          </div>
          {entry.images && entry.images.length > 0 && (
            <div className="mt-3 space-y-2">
              {entry.images.map((img, i) => (
                <img
                  key={i}
                  src={`data:${img.content_type};base64,${img.b64_data}`}
                  alt={img.prompt}
                  className="rounded-lg shadow-sm max-w-full border border-gray-200"
                />
              ))}
            </div>
          )}
          <div className="flex items-center gap-2 mt-2">
            <ConfidenceBadge level={entry.confidence} />
            {entry.mode === "agent" ? (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-copper-50 border border-copper-200 px-1.5 py-0.5 text-[10px] font-medium text-copper-600">
                <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
                Agent
              </span>
            ) : entry.mode === "normal" ? (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-blue-50 border border-blue-200 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">
                <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                </svg>
                Normal
              </span>
            ) : null}
            {entry.auto_learned && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                Auto-learned
              </span>
            )}
            {entry.sources.length > 0 && (
              <span className="text-[11px] text-gray-400">
                {entry.sources.length} source{entry.sources.length !== 1 ? "s" : ""}
              </span>
            )}
            <span className="text-[11px] text-gray-300 ml-auto">click for details</span>
          </div>
        </button>
      </div>
    </div>
  );
}
