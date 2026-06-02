"use client";

import { useState, useEffect, useCallback } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { DashboardOverview } from "@/components/dashboard/dashboard-overview";
import { ConfidenceChart } from "@/components/dashboard/confidence-chart";
import { LowConfidenceTable } from "@/components/dashboard/low-confidence-table";
import { getDashboardStats } from "@/lib/api/dashboard";
import type { DashboardStatsResponse } from "@/lib/types";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDashboardStats();
      setStats(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return (
    <PageShell
      title="Confidence Dashboard"
      description="Overview of knowledge base health and confidence distribution"
      actions={
        <Button variant="secondary" onClick={loadStats} loading={loading}>
          Refresh
        </Button>
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
          <DashboardOverview stats={stats} />
          <ConfidenceChart distribution={stats.distribution} />
          <LowConfidenceTable nodes={stats.low_confidence_nodes} />
        </div>
      )}
    </PageShell>
  );
}
