"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { PageShell } from "@/components/layout/page-shell";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { NodeDetailCard } from "@/components/nodes/node-detail-card";
import { NodeHistoryTimeline } from "@/components/nodes/node-history-timeline";
import { CorrectionForm } from "@/components/nodes/correction-form";
import { getNodeDetail } from "@/lib/api/nodes";
import { getNodeHistory } from "@/lib/api/nodes";
import type { NodeDetailResponse, NodeHistoryResponse } from "@/lib/types";

export default function NodeDetailPage() {
  const params = useParams();
  const nodeId = params.nodeId as string;

  const [node, setNode] = useState<NodeDetailResponse | null>(null);
  const [history, setHistory] = useState<NodeHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [correctionOpen, setCorrectionOpen] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nodeData, historyData] = await Promise.all([
        getNodeDetail(nodeId),
        getNodeHistory(nodeId),
      ]);
      setNode(nodeData);
      setHistory(historyData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load node");
    } finally {
      setLoading(false);
    }
  }, [nodeId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <PageShell title="Node Detail">
        <div className="flex justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell title="Node Detail">
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
          {error}
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell
      title="Node Detail"
      description={`Node ${nodeId.slice(0, 12)}...`}
      actions={
        <Button onClick={() => setCorrectionOpen(true)}>Submit Correction</Button>
      }
    >
      <div className="space-y-6 max-w-3xl">
        {node && <NodeDetailCard node={node} />}
        <NodeHistoryTimeline history={history} />
      </div>

      <CorrectionForm
        nodeId={nodeId}
        open={correctionOpen}
        onClose={() => setCorrectionOpen(false)}
        onCorrected={loadData}
      />
    </PageShell>
  );
}
