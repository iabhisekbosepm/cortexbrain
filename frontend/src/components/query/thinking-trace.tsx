"use client";

import { useState, useEffect } from "react";
import { cn, truncate } from "@/lib/utils";
import type { AgentStep } from "@/lib/types";

interface ThinkingTraceProps {
  steps: AgentStep[];
  isStreaming: boolean;
}

function StepIcon({ name, className }: { name: string; className?: string }) {
  const c = cn("h-3.5 w-3.5 shrink-0", className);

  if (name === "search_knowledge" || name === "find_entity" || name === "search_graph_text") {
    return (
      <svg className={c} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
      </svg>
    );
  }
  if (name === "activate_and_gather") {
    return (
      <svg className={c} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
      </svg>
    );
  }
  if (name === "get_node_detail" || name === "get_neighbors") {
    return (
      <svg className={c} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" />
      </svg>
    );
  }
  if (name === "check_confidence") {
    return (
      <svg className={c} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    );
  }
  if (name === "get_version_history" || name === "get_audit_logs") {
    return (
      <svg className={c} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
    );
  }
  // Default (system, unknown)
  return (
    <svg className={c} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
    </svg>
  );
}

/** Human-readable label for tool names */
function toolLabel(name: string): string {
  switch (name) {
    case "search_knowledge": return "Searching knowledge base";
    case "find_entity": return "Looking up entity";
    case "search_graph_text": return "Searching graph";
    case "activate_and_gather": return "Running spreading activation";
    case "get_node_detail": return "Inspecting node";
    case "get_neighbors": return "Exploring connections";
    case "check_confidence": return "Checking confidence";
    case "get_version_history": return "Reviewing history";
    case "get_audit_logs": return "Checking audit logs";
    case "system": return "Deepening exploration";
    default: return "Processing";
  }
}

export function ThinkingTrace({ steps, isStreaming }: ThinkingTraceProps) {
  const [expanded, setExpanded] = useState(true);

  // Auto-expand when streaming starts
  useEffect(() => {
    if (isStreaming) setExpanded(true);
  }, [isStreaming]);

  if (steps.length === 0 && !isStreaming) return null;

  // Pair tool_call + tool_result into logical steps
  const pairedSteps: { call: AgentStep; result?: AgentStep }[] = [];
  for (let i = 0; i < steps.length; i++) {
    const step = steps[i];
    if (step.type === "tool_call") {
      const next = steps[i + 1];
      if (next && next.type === "tool_result" && next.name === step.name) {
        pairedSteps.push({ call: step, result: next });
        i++; // skip the result
      } else {
        pairedSteps.push({ call: step });
      }
    }
  }

  const stepCount = pairedSteps.length;

  // Current activity: the last tool_call without a result yet, or the last completed step
  const lastStep = steps[steps.length - 1];
  const currentActivity = isStreaming && lastStep
    ? lastStep.type === "tool_call"
      ? toolLabel(lastStep.name) + "..."
      : lastStep.type === "tool_result"
        ? "Analyzing results..."
        : "Processing..."
    : null;

  // Header text
  const headerText = isStreaming
    ? stepCount > 0
      ? `Thinking... (${stepCount} step${stepCount !== 1 ? "s" : ""})`
      : "Thinking..."
    : `Reasoning (${stepCount} step${stepCount !== 1 ? "s" : ""})`;

  return (
    <div className="mb-2">
      {/* Header toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700 transition-colors py-1"
      >
        {isStreaming && (
          <svg className="h-3 w-3 animate-spin text-copper-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
        <svg
          className={cn("h-3 w-3 transition-transform", expanded ? "rotate-90" : "")}
          fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
        <span className="font-medium">{headerText}</span>
      </button>

      {/* Steps */}
      {expanded && (
        <div className="ml-1 mt-1 space-y-1.5 border-l-2 border-gray-200 pl-3">
          {pairedSteps.map((pair, i) => (
            <div key={i} className="text-xs animate-in fade-in slide-in-from-top-1 duration-300">
              {/* Tool call */}
              <div className="flex items-center gap-1.5 text-gray-600">
                <StepIcon name={pair.call.name} className="text-copper-500" />
                <span>{pair.call.content}</span>
                {pair.result && (
                  <svg className="h-3 w-3 text-green-500 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                )}
              </div>
              {/* Tool result */}
              {pair.result && (
                <div className="ml-5 mt-0.5 text-gray-400 font-mono text-[11px] leading-relaxed">
                  {truncate(pair.result.content, 200)}
                </div>
              )}
            </div>
          ))}

          {/* Current activity indicator */}
          {isStreaming && (
            <div className="flex items-center gap-1.5 text-xs text-copper-500 animate-pulse">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              <span>{currentActivity || "Processing..."}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
