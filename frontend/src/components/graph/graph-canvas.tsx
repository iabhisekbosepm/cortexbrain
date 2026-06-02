"use client";

import { useRef, useCallback, useMemo, useEffect } from "react";
import dynamic from "next/dynamic";
import type { GraphOverviewResponse, GraphNode } from "@/lib/types";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

interface GraphCanvasProps {
  data: GraphOverviewResponse;
  onNodeClick: (node: GraphNode) => void;
  highlightSearch: string;
  selectedNodeId: string | null;
}

export function GraphCanvas({ data, onNodeClick, highlightSearch, selectedNodeId }: GraphCanvasProps) {
  const graphRef = useRef<any>(null);

  const graphData = useMemo(() => ({
    nodes: data.nodes.map((n) => ({ ...n })),
    links: data.edges.map((e) => ({
      source: e.source,
      target: e.target,
      weight: e.weight,
      rel_type: e.rel_type,
    })),
  }), [data]);

  const searchLower = highlightSearch.toLowerCase();

  const isHighlighted = useCallback(
    (node: any) => {
      if (!searchLower) return false;
      return (node.name || "").toLowerCase().includes(searchLower);
    },
    [searchLower],
  );

  const nodeColor = useCallback(
    (node: any) => {
      if (node.id === selectedNodeId) return "#b45309"; // copper-700
      if (isHighlighted(node)) return "#f59e0b"; // amber-500
      if (node.confidence >= 0.8) return "#22c55e"; // green-500
      if (node.confidence >= 0.5) return "#eab308"; // yellow-500
      return "#ef4444"; // red-500
    },
    [selectedNodeId, isHighlighted],
  );

  const nodeSize = useCallback(
    (node: any) => {
      const base = Math.max(3, Math.min(12, (node.edge_count || 1) * 1.5));
      if (node.id === selectedNodeId) return base * 1.5;
      if (isHighlighted(node)) return base * 1.3;
      return base;
    },
    [selectedNodeId, isHighlighted],
  );

  const linkWidth = useCallback((link: any) => Math.max(0.5, (link.weight || 1) * 1.5), []);

  // Center on search results
  useEffect(() => {
    if (!graphRef.current || !searchLower) return;
    const match = data.nodes.find(
      (n) => n.name.toLowerCase().includes(searchLower),
    );
    if (match) {
      const graphNode = graphRef.current.graphData().nodes.find((n: any) => n.id === match.id);
      if (graphNode && graphNode.x != null) {
        graphRef.current.centerAt(graphNode.x, graphNode.y, 500);
        graphRef.current.zoom(2, 500);
      }
    }
  }, [searchLower, data.nodes]);

  return (
    <ForceGraph2D
      ref={graphRef}
      graphData={graphData}
      nodeColor={nodeColor}
      nodeVal={nodeSize}
      nodeLabel={(node: any) => `${node.name || "?"} (conf: ${(node.confidence || 0).toFixed(2)})`}
      linkWidth={linkWidth}
      linkColor={() => "#d1d5db"}
      linkDirectionalParticles={0}
      onNodeClick={(node: any) => {
        const graphNode = data.nodes.find((n) => n.id === node.id);
        if (graphNode) onNodeClick(graphNode);
      }}
      nodeCanvasObjectMode={() => "after"}
      nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D) => {
        if (!node.x || !node.y) return;
        const label = node.name || "";
        if (!label) return;
        const fontSize = 9;
        ctx.font = `${fontSize}px Sans-Serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = node.id === selectedNodeId ? "#92400e" : "#6b7280";
        const truncated = label.length > 18 ? label.slice(0, 16) + ".." : label;
        ctx.fillText(truncated, node.x, node.y + 8);
      }}
      cooldownTicks={100}
      warmupTicks={50}
    />
  );
}
