"use client";

import { Card, CardTitle } from "@/components/ui/card";
import { StatusDot } from "@/components/ui/status-dot";
import type { WorkersStatusResponse } from "@/lib/types";

export function WorkerStatusCard({ data }: { data: WorkersStatusResponse }) {
  const workerCount = data.workers.length;
  const firstWorker = data.workers[0];

  return (
    <Card className="flex items-start gap-4">
      <StatusDot
        status={data.connected ? "ok" : "error"}
        pulse={data.connected}
      />
      <div className="flex-1 min-w-0">
        <CardTitle className="text-base">
          Celery Worker {data.connected ? "Connected" : "Disconnected"}
        </CardTitle>
        <div className="mt-2 text-sm text-gray-500 space-y-1">
          {data.connected ? (
            <>
              <p>
                {workerCount} worker{workerCount !== 1 ? "s" : ""} responding
              </p>
              {firstWorker && (
                <>
                  <p>
                    Hostname:{" "}
                    <span className="font-mono text-gray-700">
                      {firstWorker.hostname}
                    </span>
                  </p>
                  {firstWorker.pid && (
                    <p>
                      PID:{" "}
                      <span className="font-mono text-gray-700">
                        {firstWorker.pid}
                      </span>
                    </p>
                  )}
                  {firstWorker.pool_size && (
                    <p>
                      Pool size:{" "}
                      <span className="font-mono text-gray-700">
                        {firstWorker.pool_size}
                      </span>
                    </p>
                  )}
                </>
              )}
              <p>
                Inspect latency:{" "}
                <span className="font-mono text-gray-700">
                  {data.latency_ms.toFixed(1)}ms
                </span>
              </p>
            </>
          ) : (
            <p className="text-red-600">
              No Celery workers are responding. Start with:{" "}
              <code className="bg-red-100 px-1.5 py-0.5 rounded text-xs font-mono">
                celery -A cortexbrain.workers.celery_app worker
              </code>
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}
