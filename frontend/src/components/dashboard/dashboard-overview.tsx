"use client";

import { Card } from "@/components/ui/card";
import type { DashboardStatsResponse } from "@/lib/types";

export function DashboardOverview({ stats }: { stats: DashboardStatsResponse }) {
  const items = [
    { label: "Total Nodes", value: stats.total_nodes.toLocaleString(), color: "text-copper-600" },
    { label: "Average Confidence", value: stats.avg_confidence.toFixed(3), color: "text-green-600" },
    {
      label: "Low Confidence (<0.5)",
      value: stats.low_confidence_nodes.length.toString(),
      color: stats.low_confidence_nodes.length > 0 ? "text-red-600" : "text-green-600",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {items.map((item) => (
        <Card key={item.label} className="text-center py-6 px-4">
          <p className={`text-3xl font-bold ${item.color}`}>{item.value}</p>
          <p className="text-sm text-gray-500 mt-1">{item.label}</p>
        </Card>
      ))}
    </div>
  );
}
