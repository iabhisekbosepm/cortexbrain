"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { timeAgo } from "@/lib/utils";

export interface IngestHistoryItem {
  id: string;
  files: string[];
  mode: "sync" | "batch";
  status: string;
  dataset: string;
  taskId?: string;
  nodesInitialized?: number;
  timestamp: Date;
}

export function IngestHistory({ items }: { items: IngestHistoryItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-gray-700">Recent Ingestions</h3>
      {items.map((item) => (
        <Card key={item.id} className="py-3 px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge className={item.mode === "sync" ? "bg-copper-100 text-copper-800 border-copper-200" : "bg-purple-100 text-purple-800 border-purple-200"}>
                {item.mode}
              </Badge>
              <span className="text-sm font-medium text-gray-800">{item.files.join(", ")}</span>
            </div>
            <span className="text-xs text-gray-400">{timeAgo(item.timestamp)}</span>
          </div>
          <div className="mt-1 text-xs text-gray-500">
            Dataset: {item.dataset}
            {item.nodesInitialized !== undefined && ` | Nodes: ${item.nodesInitialized}`}
            {item.taskId && (
              <span className="font-mono"> | Task: {item.taskId.slice(0, 8)}...</span>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}
