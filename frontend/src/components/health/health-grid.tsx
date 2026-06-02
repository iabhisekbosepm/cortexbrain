"use client";

import { Card, CardTitle } from "@/components/ui/card";
import { StatusDot } from "@/components/ui/status-dot";
import type { HealthResponse } from "@/lib/types";

const SERVICE_LABELS: Record<string, string> = {
  redis: "Redis (M_a)",
  neo4j: "Neo4j (M_s)",
  qdrant: "Qdrant (M_r)",
  postgres: "PostgreSQL (M_meta)",
  llm: "LLM Gateway",
};

export function HealthGrid({ health }: { health: HealthResponse }) {
  const services = ["redis", "neo4j", "qdrant", "postgres", "llm"] as const;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {services.map((key) => {
        const svc = health[key];
        return (
          <Card key={key} className="flex items-start gap-4">
            <StatusDot status={svc.status} pulse={svc.status === "ok"} />
            <div className="flex-1 min-w-0">
              <CardTitle className="text-sm">{SERVICE_LABELS[key]}</CardTitle>
              <div className="mt-1 text-xs text-gray-500 space-y-0.5">
                <p>Status: <span className="font-medium capitalize">{svc.status}</span></p>
                {svc.latency_ms !== null && (
                  <p>Latency: <span className="font-mono">{svc.latency_ms.toFixed(1)}ms</span></p>
                )}
                {svc.error && (
                  <p className="text-red-600 truncate" title={svc.error}>Error: {svc.error}</p>
                )}
              </div>
            </div>
          </Card>
        );
      })}
      {/* Overall status card */}
      <Card className="flex items-start gap-4 border-2 border-gray-300">
        <StatusDot status={health.status} />
        <div>
          <CardTitle className="text-sm">Overall</CardTitle>
          <p className="mt-1 text-xs font-medium capitalize text-gray-700">{health.status}</p>
        </div>
      </Card>
    </div>
  );
}
