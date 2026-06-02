"use client";

import Link from "next/link";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";

interface TopNodesTableProps {
  title: string;
  data: Record<string, unknown>[];
  valueKey: string;
  valueLabel: string;
}

export function TopNodesTable({ title, data, valueKey, valueLabel }: TopNodesTableProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <DataTable
        columns={[
          {
            header: "Node ID",
            accessor: (row: Record<string, unknown>) => {
              const id = String(row.node_id || row.id || "");
              return (
                <Link href={`/nodes/${id}`} className="text-copper-600 hover:underline font-mono text-xs">
                  {id.slice(0, 12)}...
                </Link>
              );
            },
          },
          {
            header: "Name",
            accessor: (row: Record<string, unknown>) => String(row.name || "-"),
          },
          {
            header: valueLabel,
            accessor: (row: Record<string, unknown>) => {
              const val = row[valueKey];
              return typeof val === "number" ? val.toFixed(2) : String(val || "0");
            },
            className: "text-right font-mono",
          },
        ]}
        data={data}
        emptyMessage="No data"
      />
    </Card>
  );
}
