"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ProgressBar } from "@/components/ui/progress-bar";
import { Spinner } from "@/components/ui/spinner";
import { getSessionActivations } from "@/lib/api/debug";
import type { SessionActivationsResponse } from "@/lib/types";

interface ActivationReplayProps {
  sessionId: string;
}

export function ActivationReplay({ sessionId }: ActivationReplayProps) {
  const [data, setData] = useState<SessionActivationsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  async function handleLoad() {
    setLoading(true);
    setExpanded(true);
    setError(null);
    try {
      const res = await getSessionActivations(sessionId);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load activations");
    } finally {
      setLoading(false);
    }
  }

  if (!expanded) {
    return (
      <Button variant="ghost" onClick={handleLoad} className="text-xs text-copper-600">
        Show Activation Flow
      </Button>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-2">
        <Spinner className="h-4 w-4" />
        <span className="text-xs text-gray-500">Loading activations...</span>
      </div>
    );
  }

  if (error) return <p className="text-xs text-red-500">{error}</p>;
  if (!data) return null;

  const maxScore = data.activations.reduce((max, a) => Math.max(max, a.score), 0) || 1;

  return (
    <div>
      <p className="text-[11px] text-gray-500 mb-2">
        {data.active_node_count} node{data.active_node_count !== 1 ? "s" : ""} activated
      </p>
      <div className="space-y-1.5 max-h-48 overflow-y-auto">
        {data.activations.map((entry) => (
          <div key={entry.node_id} className="flex items-center gap-2">
            <Link
              href={`/nodes/${entry.node_id}`}
              className="text-[10px] font-mono text-copper-600 hover:underline w-24 shrink-0 truncate"
            >
              {entry.node_id.slice(0, 12)}...
            </Link>
            <div className="flex-1">
              <ProgressBar value={(entry.score / maxScore) * 100} color="bg-amber-500" />
            </div>
            <span className="text-[10px] font-mono text-gray-600 w-10 text-right">
              {entry.score.toFixed(1)}
            </span>
          </div>
        ))}
        {data.activations.length === 0 && (
          <p className="text-[11px] text-gray-400 text-center py-2">No activations in this session</p>
        )}
      </div>
    </div>
  );
}
