"use client";

import { Card, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useBatchStatus } from "@/hooks/use-batch-status";
import { cn } from "@/lib/utils";

function statusColor(status: string): string {
  switch (status) {
    case "SUCCESS": return "bg-green-100 text-green-800 border-green-200";
    case "FAILURE": return "bg-red-100 text-red-800 border-red-200";
    case "STARTED": return "bg-blue-100 text-blue-800 border-blue-200";
    default: return "bg-yellow-100 text-yellow-800 border-yellow-200";
  }
}

export function BatchStatusCard({ taskId }: { taskId: string }) {
  const { status, error } = useBatchStatus(taskId);

  const isRunning = status && status.status !== "SUCCESS" && status.status !== "FAILURE";

  return (
    <Card className="flex items-start gap-3">
      {isRunning && <Spinner className="mt-1 shrink-0" />}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <CardTitle className="text-sm">Batch Task</CardTitle>
          {status && <Badge className={cn(statusColor(status.status))}>{status.status}</Badge>}
        </div>
        <p className="text-xs text-gray-500 font-mono truncate">{taskId}</p>
        {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
        {status?.error && <p className="text-xs text-red-600 mt-1">{status.error}</p>}
        {status?.result && (
          <pre className="text-xs text-gray-600 mt-2 bg-gray-50 rounded p-2 overflow-x-auto">
            {JSON.stringify(status.result, null, 2)}
          </pre>
        )}
      </div>
    </Card>
  );
}
