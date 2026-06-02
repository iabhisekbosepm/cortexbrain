"use client";

import Link from "next/link";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { ProgressBar } from "@/components/ui/progress-bar";
import { formatDate } from "@/lib/utils";
import type { LowConfidenceNode } from "@/lib/types";

export function LowConfidenceTable({ nodes }: { nodes: LowConfidenceNode[] }) {
  if (nodes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Low Confidence Nodes</CardTitle>
        </CardHeader>
        <div className="px-6 pb-6">
          <p className="text-sm text-gray-500 text-center py-6">
            No low-confidence nodes found. All knowledge has confidence &ge; 0.5.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Low Confidence Nodes ({nodes.length})</CardTitle>
      </CardHeader>
      <DataTable
        columns={[
          {
            header: "Node",
            accessor: (row: LowConfidenceNode) => (
              <Link href={`/nodes/${row.node_id}`} className="text-copper-600 hover:underline text-sm">
                {row.name || row.node_id.slice(0, 12) + "..."}
              </Link>
            ),
          },
          {
            header: "Confidence",
            accessor: (row: LowConfidenceNode) => (
              <div className="flex items-center gap-2 w-28">
                <ProgressBar
                  value={row.confidence * 100}
                  color={row.confidence < 0.3 ? "bg-red-500" : "bg-yellow-500"}
                />
                <span className="text-xs font-mono text-gray-600">{row.confidence.toFixed(2)}</span>
              </div>
            ),
          },
          {
            header: "Salience",
            accessor: (row: LowConfidenceNode) => row.salience.toFixed(3),
            className: "text-right text-sm",
          },
          {
            header: "Accesses",
            accessor: (row: LowConfidenceNode) => String(row.access_count),
            className: "text-right text-sm",
          },
          {
            header: "Last Accessed",
            accessor: (row: LowConfidenceNode) => (
              <span className="text-xs text-gray-500">{formatDate(row.last_accessed)}</span>
            ),
          },
        ]}
        data={nodes}
        emptyMessage="No low-confidence nodes"
      />
    </Card>
  );
}
