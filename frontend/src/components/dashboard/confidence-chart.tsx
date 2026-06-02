"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import type { ConfidenceBucket } from "@/lib/types";

const BUCKET_COLORS: Record<string, string> = {
  "0.0-0.3": "bg-red-500",
  "0.3-0.5": "bg-yellow-500",
  "0.5-0.8": "bg-blue-500",
  "0.8-1.0": "bg-green-500",
};

const BUCKET_LABELS: Record<string, string> = {
  "0.0-0.3": "Low",
  "0.3-0.5": "Below Medium",
  "0.5-0.8": "Medium-High",
  "0.8-1.0": "High",
};

const BUCKET_ORDER = ["0.0-0.3", "0.3-0.5", "0.5-0.8", "0.8-1.0"];

export function ConfidenceChart({ distribution }: { distribution: ConfidenceBucket[] }) {
  const maxCount = Math.max(...distribution.map((b) => b.count), 1);
  const bucketMap = Object.fromEntries(distribution.map((b) => [b.range, b.count]));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Confidence Distribution</CardTitle>
      </CardHeader>
      <div className="px-6 pb-6 space-y-3">
        {BUCKET_ORDER.map((range) => {
          const count = bucketMap[range] || 0;
          const pct = (count / maxCount) * 100;
          return (
            <div key={range} className="flex items-center gap-3">
              <div className="w-28 shrink-0">
                <span className="text-sm font-medium text-gray-700">{range}</span>
                <span className="text-[10px] text-gray-400 ml-1.5">{BUCKET_LABELS[range]}</span>
              </div>
              <div className="flex-1 h-7 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${BUCKET_COLORS[range]}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-sm font-mono text-gray-700 w-12 text-right">{count}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
