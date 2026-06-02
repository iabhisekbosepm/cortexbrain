"use client";

import { cn } from "@/lib/utils";

export type PipelineStepStatus = "pending" | "active" | "completed" | "error";

export interface PipelineStep {
  id: string;
  label: string;
  description: string;
  status: PipelineStepStatus;
  detail?: string;
}

interface PipelinePanelProps {
  steps: PipelineStep[];
  result?: {
    dataset: string;
    nodesInitialized: number;
    files: string[];
  } | null;
  error?: string | null;
}

function StepIcon({ status }: { status: PipelineStepStatus }) {
  if (status === "completed") {
    return (
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-green-100">
        <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      </div>
    );
  }
  if (status === "active") {
    return (
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-copper-600 bg-copper-50">
        <div className="h-2.5 w-2.5 rounded-full bg-copper-600 animate-pulse" />
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-red-100">
        <svg className="h-4 w-4 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
    );
  }
  return (
    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-gray-300 bg-white">
      <div className="h-2 w-2 rounded-full bg-gray-300" />
    </div>
  );
}

export function PipelinePanel({ steps, result, error }: PipelinePanelProps) {
  const isIdle = steps.every((s) => s.status === "pending");
  const isDone = steps.every((s) => s.status === "completed");

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm h-full">
      <h3 className="text-lg font-semibold text-gray-900 mb-1">Ingestion Pipeline</h3>
      <p className="text-sm text-gray-500 mb-6">
        {isIdle
          ? "Upload files and click Ingest to start the pipeline"
          : isDone
            ? "Pipeline completed successfully"
            : "Processing..."}
      </p>

      <div className="relative">
        {steps.map((step, i) => (
          <div key={step.id} className="relative flex gap-4 pb-8 last:pb-0">
            {/* Vertical connector line */}
            {i < steps.length - 1 && (
              <div
                className={cn(
                  "absolute left-[13px] top-7 h-full w-0.5",
                  step.status === "completed" ? "bg-green-200" : "bg-gray-200",
                )}
              />
            )}

            <StepIcon status={step.status} />

            <div className="flex-1 min-w-0 pt-0.5">
              <p
                className={cn(
                  "text-sm font-medium",
                  step.status === "active"
                    ? "text-copper-700"
                    : step.status === "completed"
                      ? "text-green-700"
                      : step.status === "error"
                        ? "text-red-700"
                        : "text-gray-500",
                )}
              >
                {step.label}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">{step.description}</p>
              {step.detail && (
                <p
                  className={cn(
                    "text-xs mt-1 font-mono",
                    step.status === "error" ? "text-red-500" : "text-gray-500",
                  )}
                >
                  {step.detail}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {isDone && result && (
        <div className="mt-6 rounded-lg bg-green-50 border border-green-200 p-4">
          <p className="text-sm font-medium text-green-800 mb-2">Ingestion Complete</p>
          <div className="text-xs text-green-700 space-y-1">
            <p>Dataset: <span className="font-mono">{result.dataset}</span></p>
            <p>Nodes initialized: <span className="font-semibold">{result.nodesInitialized}</span></p>
            <p>Files: {result.files.join(", ")}</p>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-lg bg-red-50 border border-red-200 p-4">
          <p className="text-sm font-medium text-red-800 mb-1">Pipeline Failed</p>
          <p className="text-xs text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}
