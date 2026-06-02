"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, truncate } from "@/lib/utils";
import type { NodeHistoryResponse } from "@/lib/types";

export function NodeHistoryTimeline({ history }: { history: NodeHistoryResponse | null }) {
  if (!history || history.history.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Version History</CardTitle>
        </CardHeader>
        <p className="text-sm text-gray-500">No version history available.</p>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Version History</CardTitle>
          <Badge className="bg-gray-100 text-gray-700 border-gray-200">
            v{history.current_version}
          </Badge>
        </div>
      </CardHeader>

      <div className="relative ml-3">
        {/* Timeline line */}
        <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gray-200" />

        {history.history.map((version, i) => (
          <div key={version.version} className="relative pl-6 pb-6 last:pb-0">
            {/* Timeline dot */}
            <div
              className={`absolute left-0 top-1 h-2.5 w-2.5 rounded-full -translate-x-1 ${
                i === 0 ? "bg-copper-600" : "bg-gray-400"
              }`}
            />

            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Badge className="bg-gray-100 text-gray-700 border-gray-200">
                    v{version.version}
                  </Badge>
                  <span className="text-xs text-gray-500">{formatDate(version.timestamp)}</span>
                </div>
                <p className="text-sm text-gray-800">{truncate(version.value, 200)}</p>
                {version.reason && (
                  <p className="text-xs text-gray-500 mt-1">Reason: {version.reason}</p>
                )}
                <p className="text-xs text-gray-400 mt-0.5">
                  by {version.changed_by}
                  {version.source && ` via ${version.source}`}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
