"use client";

import { cn, timeAgo } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { StatusDot } from "@/components/ui/status-dot";
import { StageCard } from "./stage-card";
import type { PipelineState } from "@/lib/types";

interface PipelineRowProps {
  pipeline: PipelineState;
}

export function PipelineRow({ pipeline }: PipelineRowProps) {
  const hasFailed = pipeline.stages.some((s) => s.status === "failed");
  const allDone = pipeline.stages.every((s) => s.status === "completed");
  const overallStatus = pipeline.isRunning
    ? "running"
    : hasFailed
      ? "failed"
      : allDone
        ? "completed"
        : "idle";

  const statusDotValue =
    overallStatus === "running"
      ? "ok"
      : overallStatus === "completed"
        ? "healthy"
        : overallStatus === "failed"
          ? "error"
          : "degraded";

  const scheduleColors: Record<string, string> = {
    "Every 30s": "bg-blue-50 text-blue-700 border-blue-200",
    "Every 1hr": "bg-purple-50 text-purple-700 border-purple-200",
    Weekly: "bg-yellow-50 text-yellow-700 border-yellow-200",
    "On-demand": "bg-gray-100 text-gray-600 border-gray-200",
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <StatusDot
            status={statusDotValue}
            pulse={overallStatus === "running"}
            size="md"
          />
          <div>
            <h3 className="text-base font-semibold text-gray-900">
              {pipeline.label}
            </h3>
            <p className="text-xs text-gray-500">{pipeline.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            className={
              scheduleColors[pipeline.schedule] ||
              "bg-gray-100 text-gray-600 border-gray-200"
            }
          >
            {pipeline.schedule}
          </Badge>
          {pipeline.lastRunTime && (
            <span className="text-xs text-gray-400">
              Last: {timeAgo(new Date(pipeline.lastRunTime))}
            </span>
          )}
        </div>
      </div>

      {/* Horizontal stage flow */}
      <div className="flex items-center overflow-x-auto pb-2">
        {pipeline.stages.map((stage, i) => (
          <StageCard key={stage.name} stage={stage} isFirst={i === 0} />
        ))}
      </div>

      {/* Last run result metrics */}
      {Object.keys(pipeline.lastRunResult).length > 0 && !pipeline.isRunning && (
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-gray-500 border-t border-gray-100 pt-3">
          {Object.entries(pipeline.lastRunResult).map(([key, val]) => (
            <div key={key}>
              <span className="text-gray-400">
                {key.replace(/_/g, " ")}:
              </span>{" "}
              <span className="font-mono font-medium text-gray-700">
                {typeof val === "number" ? val : String(val)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
