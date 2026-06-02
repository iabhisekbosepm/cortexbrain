"use client";

import { Card } from "@/components/ui/card";
import type { WorkersStatusResponse } from "@/lib/types";

export function WorkerStats({ data }: { data: WorkersStatusResponse }) {
  const totalProcessed = data.workers.reduce(
    (sum, w) => sum + w.total_tasks_processed,
    0,
  );

  const items = [
    {
      label: "Tasks Processed",
      value: totalProcessed,
      color: "text-copper-600",
    },
    {
      label: "Active Tasks",
      value: data.active_tasks.length,
      color: "text-green-600",
    },
    {
      label: "Registered Tasks",
      value: data.registered_tasks.length,
      color: "text-purple-600",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {items.map((item) => (
        <Card key={item.label} className="text-center py-6">
          <p className={`text-3xl font-bold ${item.color}`}>
            {item.value.toLocaleString()}
          </p>
          <p className="text-sm text-gray-500 mt-1">{item.label}</p>
        </Card>
      ))}
    </div>
  );
}
