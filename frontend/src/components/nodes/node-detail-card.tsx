"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, ConfidenceBadge } from "@/components/ui/badge";
import { ProgressBar } from "@/components/ui/progress-bar";
import { CodeBlock } from "@/components/ui/code-block";
import { formatDate } from "@/lib/utils";
import type { ConfidenceLevel, NodeDetailResponse } from "@/lib/types";

function confidenceLevel(score: number): ConfidenceLevel {
  if (score >= 0.8) return "high";
  if (score >= 0.5) return "medium";
  return "low";
}

export function NodeDetailCard({ node }: { node: NodeDetailResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{node.name || "Unnamed Node"}</CardTitle>
        <p className="text-xs text-gray-500 font-mono mt-1">{node.node_id}</p>
      </CardHeader>

      {node.description && (
        <p className="text-sm text-gray-700 mb-4">{node.description}</p>
      )}

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-500 mb-1">Confidence</p>
          <div className="flex items-center gap-2">
            <ProgressBar value={node.confidence * 100} color="bg-green-500" />
            <span className="text-sm font-mono">{node.confidence.toFixed(2)}</span>
          </div>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Salience</p>
          <div className="flex items-center gap-2">
            <ProgressBar value={node.salience * 100} color="bg-copper-500" />
            <span className="text-sm font-mono">{node.salience.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <ConfidenceBadge level={confidenceLevel(node.confidence)} />
        {node.conflicted && (
          <Badge className="bg-purple-100 text-purple-800 border-purple-200">Conflicted</Badge>
        )}
        {node.volatile && (
          <Badge className="bg-orange-100 text-orange-800 border-orange-200">Volatile</Badge>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm mb-4">
        <Stat label="Access Count" value={node.access_count} />
        <Stat label="Corrections" value={node.correction_count} />
        <Stat label="Edge Count" value={node.edge_count} />
        <Stat label="Last Accessed" value={formatDate(node.last_accessed)} />
      </div>

      {Object.keys(node.properties).length > 0 && (
        <div>
          <p className="text-xs text-gray-500 font-medium mb-2">Raw Properties</p>
          <CodeBlock>{JSON.stringify(node.properties, null, 2)}</CodeBlock>
        </div>
      )}
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="font-semibold text-gray-900">{value}</p>
    </div>
  );
}
