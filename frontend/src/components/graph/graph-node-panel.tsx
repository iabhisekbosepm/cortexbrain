"use client";

import { useState } from "react";
import Link from "next/link";
import { ConfidenceBadge, Badge } from "@/components/ui/badge";
import { ProgressBar } from "@/components/ui/progress-bar";
import { Button } from "@/components/ui/button";
import { CorrectionForm } from "@/components/nodes/correction-form";
import { truncate } from "@/lib/utils";
import type { GraphNode, ConfidenceLevel } from "@/lib/types";

function confidenceLevel(score: number): ConfidenceLevel {
  if (score >= 0.8) return "high";
  if (score >= 0.5) return "medium";
  return "low";
}

interface GraphNodePanelProps {
  node: GraphNode;
  onClose: () => void;
}

export function GraphNodePanel({ node, onClose }: GraphNodePanelProps) {
  const [correctionOpen, setCorrectionOpen] = useState(false);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 shrink-0">
        <h3 className="text-sm font-semibold text-gray-900">Node Detail</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 text-lg leading-none"
        >
          &times;
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Name & ID */}
        <div>
          <p className="font-semibold text-gray-900 text-lg">{node.name || "Unnamed"}</p>
          <p className="text-xs text-gray-400 font-mono mt-0.5">{node.id}</p>
        </div>

        {/* Description */}
        {node.description && (
          <p className="text-sm text-gray-700 leading-relaxed">
            {truncate(node.description, 300)}
          </p>
        )}

        {/* Confidence */}
        <div>
          <p className="text-xs text-gray-500 mb-1.5">Confidence</p>
          <div className="flex items-center gap-2">
            <ConfidenceBadge level={confidenceLevel(node.confidence)} />
            <div className="flex-1">
              <ProgressBar
                value={node.confidence * 100}
                color={
                  node.confidence >= 0.8
                    ? "bg-green-500"
                    : node.confidence >= 0.5
                      ? "bg-yellow-500"
                      : "bg-red-500"
                }
              />
            </div>
            <span className="text-sm font-mono text-gray-600">{node.confidence.toFixed(2)}</span>
          </div>
        </div>

        {/* Salience */}
        <div>
          <p className="text-xs text-gray-500 mb-1.5">Salience</p>
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <ProgressBar value={node.salience * 100} color="bg-copper-500" />
            </div>
            <span className="text-sm font-mono text-gray-600">{node.salience.toFixed(3)}</span>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <p className="text-lg font-semibold text-gray-900">{node.edge_count}</p>
            <p className="text-xs text-gray-500">Edges</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <p className="text-lg font-semibold text-gray-900">{node.access_count}</p>
            <p className="text-xs text-gray-500">Accesses</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Link href={`/nodes/${node.id}`}>
            <Button variant="secondary" className="text-xs">
              Full Detail
            </Button>
          </Link>
          <Button onClick={() => setCorrectionOpen(true)} className="text-xs">
            Correct
          </Button>
        </div>
      </div>

      <CorrectionForm
        nodeId={node.id}
        open={correctionOpen}
        onClose={() => setCorrectionOpen(false)}
        onCorrected={() => setCorrectionOpen(false)}
      />
    </div>
  );
}
