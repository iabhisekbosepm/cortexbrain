"use client";

import { useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ProgressBar } from "@/components/ui/progress-bar";
import { useToast } from "@/components/ui/toast";
import { approveNode, rejectNode } from "@/lib/api/review";
import { CorrectionForm } from "@/components/nodes/correction-form";
import { formatDate, truncate } from "@/lib/utils";
import type { ReviewNodeEntry } from "@/lib/types";

interface ReviewQueueProps {
  nodes: ReviewNodeEntry[];
  onAction: () => void;
}

export function ReviewQueue({ nodes, onAction }: ReviewQueueProps) {
  return (
    <div className="space-y-3">
      {nodes.map((node) => (
        <ReviewCard key={node.node_id} node={node} onAction={onAction} />
      ))}
    </div>
  );
}

function ReviewCard({ node, onAction }: { node: ReviewNodeEntry; onAction: () => void }) {
  const { toast } = useToast();
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [correctionOpen, setCorrectionOpen] = useState(false);

  async function handleApprove() {
    setApproving(true);
    try {
      await approveNode(node.node_id);
      toast(`Approved "${truncate(node.name || "node", 30)}" — confidence set to 0.8`, "success");
      onAction();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Approve failed", "error");
    } finally {
      setApproving(false);
    }
  }

  async function handleReject() {
    setRejecting(true);
    try {
      await rejectNode(node.node_id);
      toast(`Rejected "${truncate(node.name || "node", 30)}" — archived`, "success");
      onAction();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Reject failed", "error");
    } finally {
      setRejecting(false);
    }
  }

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Link
              href={`/nodes/${node.node_id}`}
              className="font-medium text-gray-900 hover:text-copper-700 truncate"
            >
              {node.name || "Unnamed Node"}
            </Link>
            <Badge className="bg-amber-100 text-amber-700 border-amber-200 text-[10px] shrink-0">
              Auto-learned
            </Badge>
          </div>
          <p className="text-xs text-gray-400 font-mono mt-0.5">{node.node_id}</p>

          {node.description && (
            <p className="text-sm text-gray-600 mt-2 leading-relaxed">
              {truncate(node.description, 200)}
            </p>
          )}

          <div className="flex items-center gap-4 mt-3 text-xs text-gray-500 flex-wrap">
            <div className="flex items-center gap-1.5">
              <span>Confidence:</span>
              <div className="w-16">
                <ProgressBar value={node.confidence * 100} color="bg-yellow-500" />
              </div>
              <span className="font-mono">{node.confidence.toFixed(2)}</span>
            </div>
            <span>Salience: {node.salience.toFixed(3)}</span>
            <span>Accesses: {node.access_count}</span>
            {node.last_accessed && <span>Last: {formatDate(node.last_accessed)}</span>}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="ghost"
            onClick={() => setCorrectionOpen(true)}
            className="text-xs"
          >
            Edit
          </Button>
          <Button
            variant="secondary"
            onClick={handleReject}
            loading={rejecting}
            className="text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            Reject
          </Button>
          <Button onClick={handleApprove} loading={approving} className="text-xs">
            Approve
          </Button>
        </div>
      </div>

      <CorrectionForm
        nodeId={node.node_id}
        open={correctionOpen}
        onClose={() => setCorrectionOpen(false)}
        onCorrected={onAction}
      />
    </Card>
  );
}
