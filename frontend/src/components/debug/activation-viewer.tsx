"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ProgressBar } from "@/components/ui/progress-bar";
import { Spinner } from "@/components/ui/spinner";
import { getSessionActivations } from "@/lib/api/debug";
import type { SessionActivationsResponse } from "@/lib/types";

export function ActivationViewer() {
  const [sessionId, setSessionId] = useState("");
  const [data, setData] = useState<SessionActivationsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLookup() {
    const trimmed = sessionId.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getSessionActivations(trimmed);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load activations");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  const maxScore = data?.activations.reduce((max, a) => Math.max(max, a.score), 0) || 100;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Session Activations</CardTitle>
      </CardHeader>

      <div className="flex gap-2 mb-4">
        <div className="flex-1">
          <Input
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            placeholder="Enter session UUID"
            className="font-mono text-sm"
            onKeyDown={(e) => e.key === "Enter" && handleLookup()}
          />
        </div>
        <Button onClick={handleLookup} loading={loading}>
          Lookup
        </Button>
      </div>

      {loading && (
        <div className="flex justify-center py-4">
          <Spinner />
        </div>
      )}

      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}

      {data && (
        <div>
          <p className="text-xs text-gray-500 mb-3">
            {data.active_node_count} active node{data.active_node_count !== 1 ? "s" : ""}
          </p>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {data.activations.map((entry) => (
              <div key={entry.node_id} className="flex items-center gap-3">
                <Link
                  href={`/nodes/${entry.node_id}`}
                  className="text-xs font-mono text-copper-600 hover:underline w-28 shrink-0 truncate"
                >
                  {entry.node_id.slice(0, 12)}...
                </Link>
                <div className="flex-1">
                  <ProgressBar value={(entry.score / maxScore) * 100} color="bg-amber-500" />
                </div>
                <span className="text-xs font-mono text-gray-600 w-12 text-right">{entry.score.toFixed(1)}</span>
              </div>
            ))}
            {data.activations.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">No activations for this session</p>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
