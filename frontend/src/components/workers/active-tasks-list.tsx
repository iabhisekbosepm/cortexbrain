"use client";

import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import type { ActiveTask } from "@/lib/types";

interface ActiveTasksListProps {
  activeTasks: ActiveTask[];
  reservedTasks: ActiveTask[];
}

function shortName(fullName: string) {
  const parts = fullName.split(".");
  return parts[parts.length - 1];
}

function formatRuntime(seconds: number | null) {
  if (seconds === null) return null;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

export function ActiveTasksList({
  activeTasks,
  reservedTasks,
}: ActiveTasksListProps) {
  const hasAny = activeTasks.length > 0 || reservedTasks.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Tasks</CardTitle>
        <CardDescription>Currently executing and queued tasks</CardDescription>
      </CardHeader>

      {!hasAny && (
        <EmptyState
          title="No active tasks"
          description="All workers are idle. Tasks run on schedule via Celery Beat."
        />
      )}

      {activeTasks.length > 0 && (
        <div className="space-y-3 px-6 pb-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Executing ({activeTasks.length})
          </p>
          {activeTasks.map((task) => (
            <div
              key={task.task_id}
              className="rounded-lg border border-green-200 bg-green-50 p-3"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm text-gray-900">
                  {shortName(task.task_name)}
                </span>
                <Badge className="bg-green-100 text-green-800 border-green-200">
                  Running
                </Badge>
              </div>
              <div className="mt-1 text-xs text-gray-500 space-y-0.5">
                <p>
                  ID:{" "}
                  <span className="font-mono">
                    {task.task_id.slice(0, 8)}...
                  </span>
                </p>
                {task.worker && <p>Worker: {task.worker}</p>}
                {task.runtime_seconds !== null && (
                  <p>Runtime: {formatRuntime(task.runtime_seconds)}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {reservedTasks.length > 0 && (
        <div className="space-y-3 px-6 pb-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Queued ({reservedTasks.length})
          </p>
          {reservedTasks.map((task) => (
            <div
              key={task.task_id}
              className="rounded-lg border border-yellow-200 bg-yellow-50 p-3"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm text-gray-900">
                  {shortName(task.task_name)}
                </span>
                <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">
                  Queued
                </Badge>
              </div>
              <p className="mt-1 text-xs text-gray-500 font-mono">
                {task.task_id.slice(0, 8)}...
              </p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
