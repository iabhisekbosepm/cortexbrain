"use client";

import { useState, useEffect, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { GraphCanvas } from "@/components/graph/graph-canvas";
import { GraphNodePanel } from "@/components/graph/graph-node-panel";
import { getGraphOverview, getGraphSubgraph } from "@/lib/api/graph";
import type { GraphOverviewResponse, GraphNode } from "@/lib/types";

export default function GraphPage() {
  const [data, setData] = useState<GraphOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getGraphOverview(200);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  async function handleNodeClick(node: GraphNode) {
    setSelectedNode(node);
    // Load subgraph centered on clicked node to expand the view
    try {
      const subgraph = await getGraphSubgraph(node.id, 1);
      if (data && subgraph.nodes.length > 0) {
        // Merge subgraph nodes and edges into existing data
        const existingIds = new Set(data.nodes.map((n) => n.id));
        const newNodes = subgraph.nodes.filter((n) => !existingIds.has(n.id));
        const existingEdgeKeys = new Set(
          data.edges.map((e) => `${e.source}-${e.target}`),
        );
        const newEdges = subgraph.edges.filter(
          (e) =>
            !existingEdgeKeys.has(`${e.source}-${e.target}`) &&
            !existingEdgeKeys.has(`${e.target}-${e.source}`),
        );
        if (newNodes.length > 0 || newEdges.length > 0) {
          setData({
            nodes: [...data.nodes, ...newNodes],
            edges: [...data.edges, ...newEdges],
          });
        }
      }
    } catch {
      // Subgraph expansion is best-effort
    }
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-6 py-3 border-b border-gray-200 bg-white shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Knowledge Graph</h2>
              <p className="text-xs text-gray-500">
                Interactive visualization of knowledge nodes and relationships
                {data && (
                  <span className="ml-2 text-gray-400">
                    ({data.nodes.length} nodes, {data.edges.length} edges)
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search nodes..."
                className="w-56 text-sm"
              />
              <Button variant="secondary" onClick={loadOverview} loading={loading} className="text-xs">
                Refresh
              </Button>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="px-6 py-2 bg-white border-b border-gray-100 shrink-0">
          <div className="flex items-center gap-4 text-[11px] text-gray-500">
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-green-500 inline-block" /> High (&ge;0.8)
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-yellow-500 inline-block" /> Medium (&ge;0.5)
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-red-500 inline-block" /> Low (&lt;0.5)
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-amber-500 inline-block" /> Search match
            </span>
          </div>
        </div>

        {/* Graph canvas */}
        <div className="flex-1 relative bg-gray-50">
          {loading && !data && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <Spinner className="h-8 w-8 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Loading knowledge graph...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="rounded-lg bg-red-50 border border-red-200 p-6 max-w-md text-center">
                <p className="text-sm text-red-700">{error}</p>
                <Button variant="secondary" onClick={loadOverview} className="mt-3 text-xs">
                  Retry
                </Button>
              </div>
            </div>
          )}

          {data && data.nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center text-gray-500">
                <p className="text-lg font-medium">No nodes in the knowledge graph</p>
                <p className="text-sm mt-1">Ingest some documents to populate the graph.</p>
              </div>
            </div>
          )}

          {data && data.nodes.length > 0 && (
            <GraphCanvas
              data={data}
              onNodeClick={handleNodeClick}
              highlightSearch={searchTerm}
              selectedNodeId={selectedNode?.id || null}
            />
          )}
        </div>
      </div>

      {/* Right sidebar: node detail */}
      {selectedNode && (
        <div className="w-80 border-l border-gray-200 bg-white shrink-0 hidden lg:flex flex-col">
          <GraphNodePanel
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
          />
        </div>
      )}
    </div>
  );
}
