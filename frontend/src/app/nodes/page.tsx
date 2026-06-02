"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { PageShell } from "@/components/layout/page-shell";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { NodeSearch } from "@/components/nodes/node-search";
import { DataTable } from "@/components/ui/data-table";
import { Spinner } from "@/components/ui/spinner";
import { getDebugStats } from "@/lib/api/debug";
import type { DebugStatsResponse } from "@/lib/types";

export default function NodesPage() {
  const [stats, setStats] = useState<DebugStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getDebugStats();
        setStats(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load stats");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <PageShell title="Node Explorer" description="Search and browse knowledge graph nodes">
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Lookup Node by UUID</CardTitle>
          </CardHeader>
          <NodeSearch />
        </Card>

        {loading && (
          <div className="flex justify-center py-8">
            <Spinner className="h-8 w-8" />
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {stats && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Top Accessed Nodes</CardTitle>
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
                    header: "Accesses",
                    accessor: (row: Record<string, unknown>) => String(row.access_count || 0),
                    className: "text-right",
                  },
                ]}
                data={stats.top_accessed_nodes}
                emptyMessage="No accessed nodes"
              />
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Top Salient Nodes</CardTitle>
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
                    header: "Salience",
                    accessor: (row: Record<string, unknown>) => Number(row.salience || 0).toFixed(2),
                    className: "text-right",
                  },
                ]}
                data={stats.top_salient_nodes}
                emptyMessage="No salient nodes"
              />
            </Card>
          </div>
        )}
      </div>
    </PageShell>
  );
}
