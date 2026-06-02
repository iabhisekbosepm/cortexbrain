"use client";

import { Card } from "@/components/ui/card";
import type { DebugStatsResponse } from "@/lib/types";

export function StatsOverview({ stats }: { stats: DebugStatsResponse }) {
  const items = [
    { label: "Total Entities", value: stats.total_entities, color: "text-copper-600" },
    { label: "Active Sessions", value: stats.active_sessions, color: "text-green-600" },
    { label: "Metadata Rows", value: stats.total_metadata_rows, color: "text-purple-600" },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {items.map((item) => (
        <Card key={item.label} className="text-center py-6">
          <p className={`text-3xl font-bold ${item.color}`}>{item.value.toLocaleString()}</p>
          <p className="text-sm text-gray-500 mt-1">{item.label}</p>
        </Card>
      ))}
    </div>
  );
}
