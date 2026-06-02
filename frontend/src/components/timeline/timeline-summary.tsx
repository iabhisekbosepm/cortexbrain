"use client";

import { Card } from "@/components/ui/card";
import type { TimelineSummary as TimelineSummaryType } from "@/lib/types";

const stats = [
  { key: "total_events", label: "Total Events", color: "bg-gray-500" },
  { key: "corrections", label: "Corrections", color: "bg-copper-600" },
  { key: "ingestions", label: "Ingestions", color: "bg-blue-500" },
  { key: "decays", label: "Decays", color: "bg-amber-500" },
  { key: "consolidations", label: "Consolidations", color: "bg-purple-500" },
  { key: "continuous_learning", label: "Auto-learned", color: "bg-green-500" },
] as const;

export function TimelineSummaryCards({ summary }: { summary: TimelineSummaryType }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
      {stats.map(({ key, label, color }) => (
        <Card key={key} className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              {label}
            </span>
          </div>
          <p className="text-2xl font-bold text-gray-900">
            {summary[key].toLocaleString()}
          </p>
        </Card>
      ))}
    </div>
  );
}
