"use client";

import { StatusDot } from "@/components/ui/status-dot";
import { timeAgo } from "@/lib/utils";
import type { HealthHistoryEntry } from "@/lib/types";

export function HealthHistory({ history }: { history: HealthHistoryEntry[] }) {
  if (history.length === 0) {
    return <p className="text-sm text-gray-500">No checks yet.</p>;
  }

  return (
    <div className="space-y-2 max-h-80 overflow-y-auto">
      {history.map((entry, i) => (
        <div key={i} className="flex items-center gap-3 text-sm py-1.5 border-b border-gray-100 last:border-0">
          <StatusDot status={entry.status} size="sm" pulse={false} />
          <span className="capitalize font-medium text-gray-700 w-20">{entry.status}</span>
          <div className="flex gap-2 flex-1">
            {Object.entries(entry.services).map(([name, status]) => (
              <span key={name} className="flex items-center gap-1 text-xs text-gray-500">
                <StatusDot status={status} size="sm" pulse={false} />
                {name}
              </span>
            ))}
          </div>
          <span className="text-xs text-gray-400">{timeAgo(entry.timestamp)}</span>
        </div>
      ))}
    </div>
  );
}
