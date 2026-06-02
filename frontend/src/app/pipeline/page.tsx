"use client";

import { PageShell } from "@/components/layout/page-shell";
import { PipelineRow } from "@/components/pipeline/pipeline-row";
import { ConnectionStatus } from "@/components/pipeline/connection-status";
import { usePipelineStream } from "@/hooks/use-pipeline-stream";
import type { PipelineType } from "@/lib/types";

const PIPELINE_ORDER: PipelineType[] = [
  "decay",
  "salience",
  "consolidation",
  "ingestion",
];

export default function PipelineMonitorPage() {
  const { pipelines, connected, error } = usePipelineStream();

  return (
    <PageShell
      title="Pipeline Monitor"
      description="Real-time stage-by-stage view of all background pipelines"
      actions={<ConnectionStatus connected={connected} error={error} />}
    >
      <div className="space-y-6">
        {PIPELINE_ORDER.map((type) => (
          <PipelineRow key={type} pipeline={pipelines[type]} />
        ))}
      </div>
    </PageShell>
  );
}
