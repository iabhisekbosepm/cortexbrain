"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { WorkerStatusCard } from "@/components/workers/worker-status-card";
import { WorkerStats } from "@/components/workers/worker-stats";
import { BeatScheduleTable } from "@/components/workers/beat-schedule-table";
import { ActiveTasksList } from "@/components/workers/active-tasks-list";
import { getWorkersStatus } from "@/lib/api/workers";
import type { WorkersStatusResponse } from "@/lib/types";

export default function WorkersPage() {
  const [data, setData] = useState<WorkersStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const status = await getWorkersStatus();
      setData(status);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load worker status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(loadStatus, 10000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, loadStatus]);

  return (
    <PageShell
      title="Workers"
      description="Celery worker health, task execution, and beat schedule"
      actions={
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300"
            />
            Auto-refresh (10s)
          </label>
          <Button
            variant="secondary"
            onClick={() => {
              setLoading(true);
              loadStatus();
            }}
            loading={loading}
          >
            Refresh
          </Button>
        </div>
      }
    >
      {error && !data && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700 mb-6">
          {error}. Check your API settings.
        </div>
      )}

      {!data && loading && (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {data && (
        <div className="space-y-6">
          <WorkerStatusCard data={data} />
          <WorkerStats data={data} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <BeatScheduleTable schedule={data.beat_schedule} />
            <ActiveTasksList
              activeTasks={data.active_tasks}
              reservedTasks={data.reserved_tasks}
            />
          </div>
        </div>
      )}
    </PageShell>
  );
}
