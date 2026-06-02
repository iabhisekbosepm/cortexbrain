"use client";

import { useState, useEffect, useCallback } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { StatsOverview } from "@/components/debug/stats-overview";
import { TopNodesTable } from "@/components/debug/top-nodes-table";
import { ActivationViewer } from "@/components/debug/activation-viewer";
import { SalienceRecomputeButton } from "@/components/debug/salience-recompute-button";
import { getDebugStats } from "@/lib/api/debug";
import type { DebugStatsResponse } from "@/lib/types";

export default function DebugPage() {
  const [stats, setStats] = useState<DebugStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDebugStats();
      setStats(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load stats");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return (
    <PageShell
      title="Debug Dashboard"
      description="Inspect system stats, activations, and salience scores"
      actions={
        <div className="flex items-center gap-2">
          <SalienceRecomputeButton onComplete={loadStats} />
          <Button variant="secondary" onClick={loadStats} loading={loading}>
            Refresh Stats
          </Button>
        </div>
      }
    >
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700 mb-6">
          {error}
        </div>
      )}

      {loading && !stats && (
        <div className="flex justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {stats && (
        <div className="space-y-6">
          <StatsOverview stats={stats} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <TopNodesTable
              title="Top Accessed Nodes"
              data={stats.top_accessed_nodes}
              valueKey="access_count"
              valueLabel="Accesses"
            />
            <TopNodesTable
              title="Top Salient Nodes"
              data={stats.top_salient_nodes}
              valueKey="salience"
              valueLabel="Salience"
            />
          </div>

          <ActivationViewer />
        </div>
      )}
    </PageShell>
  );
}
