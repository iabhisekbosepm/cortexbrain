"use client";

import { useState } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { HealthGrid } from "@/components/health/health-grid";
import { HealthHistory } from "@/components/health/health-history";
import { useHealth } from "@/hooks/use-health";

export default function HealthPage() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const { health, loading, error, history, refresh } = useHealth(autoRefresh, 10000);

  return (
    <PageShell
      title="Health Monitor"
      description="Real-time status of all CortexBrain services"
      actions={
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300"
            />
            Auto-refresh (10s)
          </label>
          <Button variant="secondary" onClick={refresh} loading={loading}>
            Refresh Now
          </Button>
        </div>
      }
    >
      {error && !health && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700 mb-6">
          {error}. Check your API settings.
        </div>
      )}

      {!health && loading && (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {health && (
        <div className="space-y-6">
          <HealthGrid health={health} />

          <Card>
            <CardHeader>
              <CardTitle>Check History (last 20)</CardTitle>
            </CardHeader>
            <HealthHistory history={history} />
          </Card>
        </div>
      )}
    </PageShell>
  );
}
