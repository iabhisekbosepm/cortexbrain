"use client";

import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import type { BeatScheduleEntry } from "@/lib/types";

export function BeatScheduleTable({
  schedule,
}: {
  schedule: BeatScheduleEntry[];
}) {
  const columns = [
    {
      header: "Name",
      accessor: (row: BeatScheduleEntry) => (
        <span className="font-medium text-gray-900">{row.name}</span>
      ),
    },
    {
      header: "Interval",
      accessor: (row: BeatScheduleEntry) => (
        <Badge className="bg-copper-100 text-copper-800 border-copper-200">
          {row.interval_human}
        </Badge>
      ),
    },
    {
      header: "Description",
      accessor: (row: BeatScheduleEntry) => (
        <span className="text-gray-600">{row.description}</span>
      ),
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Beat Schedule</CardTitle>
        <CardDescription>
          Periodic tasks configured via Celery Beat
        </CardDescription>
      </CardHeader>
      <DataTable
        columns={columns}
        data={schedule}
        emptyMessage="No beat schedule configured"
      />
    </Card>
  );
}
