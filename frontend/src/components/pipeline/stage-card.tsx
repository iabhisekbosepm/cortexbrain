"use client";

import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/spinner";
import type { PipelineStageState } from "@/lib/types";

interface StageCardProps {
  stage: PipelineStageState;
  isFirst: boolean;
}

export function StageCard({ stage, isFirst }: StageCardProps) {
  const statusStyles = {
    idle: "border-gray-200 bg-gray-50",
    running: "border-copper-400 bg-copper-50 ring-2 ring-copper-200",
    completed: "border-green-300 bg-green-50",
    failed: "border-red-300 bg-red-50",
  }[stage.status];

  const connectorColor = {
    idle: "bg-gray-200",
    running: "bg-copper-300",
    completed: "bg-green-300",
    failed: "bg-red-300",
  }[stage.status];

  return (
    <div className="flex items-center shrink-0">
      {/* Connector line */}
      {!isFirst && (
        <div className="flex items-center shrink-0">
          <div className={cn("w-6 h-0.5", connectorColor)} />
          <svg className={cn("h-3 w-3 -ml-1.5", stage.status === "completed" ? "text-green-300" : stage.status === "running" ? "text-copper-300" : "text-gray-200")} viewBox="0 0 12 12" fill="currentColor">
            <path d="M2 1l8 5-8 5V1z" />
          </svg>
        </div>
      )}

      {/* Stage card */}
      <div
        className={cn(
          "rounded-lg border p-3 min-w-[150px] max-w-[190px] transition-all duration-300",
          statusStyles,
        )}
      >
        {/* Status icon + label */}
        <div className="flex items-center gap-2 mb-1">
          <StageIcon status={stage.status} />
          <span
            className={cn(
              "text-sm font-medium truncate",
              stage.status === "running" && "text-copper-700",
              stage.status === "completed" && "text-green-700",
              stage.status === "failed" && "text-red-700",
              stage.status === "idle" && "text-gray-500",
            )}
          >
            {stage.label}
          </span>
        </div>

        {/* Description */}
        <p className="text-xs text-gray-400 mb-2 line-clamp-2">
          {stage.description}
        </p>

        {/* Metrics */}
        {Object.keys(stage.metrics).length > 0 && (
          <div className="space-y-0.5">
            {Object.entries(stage.metrics).map(([key, val]) => (
              <div key={key} className="flex justify-between text-xs">
                <span className="text-gray-500">{formatMetricKey(key)}</span>
                <span className="font-mono text-gray-700">{val}</span>
              </div>
            ))}
          </div>
        )}

        {/* Duration */}
        {stage.duration_ms !== null && (
          <div className="mt-1 text-xs text-gray-400 font-mono">
            {stage.duration_ms < 1000
              ? `${stage.duration_ms}ms`
              : `${(stage.duration_ms / 1000).toFixed(1)}s`}
          </div>
        )}

        {/* Error */}
        {stage.error && (
          <div
            className="mt-1 text-xs text-red-500 truncate"
            title={stage.error}
          >
            {stage.error}
          </div>
        )}
      </div>
    </div>
  );
}

function StageIcon({ status }: { status: string }) {
  if (status === "running") return <Spinner className="h-4 w-4" />;
  if (status === "completed")
    return (
      <svg
        className="h-4 w-4 text-green-600"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth="2"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M4.5 12.75l6 6 9-13.5"
        />
      </svg>
    );
  if (status === "failed")
    return (
      <svg
        className="h-4 w-4 text-red-600"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth="2"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M6 18L18 6M6 6l12 12"
        />
      </svg>
    );
  return <div className="h-3 w-3 rounded-full bg-gray-300 shrink-0" />;
}

function formatMetricKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
