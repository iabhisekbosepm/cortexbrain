"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { connectPipelineStream, getPipelineStatus } from "@/lib/api/pipeline";
import type {
  PipelineEvent,
  PipelineState,
  PipelineStageState,
  PipelineStageStatus,
  PipelineType,
} from "@/lib/types";

// Static stage definitions for each pipeline
const PIPELINE_DEFINITIONS: Record<
  PipelineType,
  {
    label: string;
    description: string;
    schedule: string;
    stages: { name: string; label: string; description: string }[];
  }
> = {
  decay: {
    label: "Decay Cycle",
    description:
      "Decrements activation scores, evicts expired nodes from Redis",
    schedule: "Every 30s",
    stages: [
      {
        name: "scan_sessions",
        label: "Scan Sessions",
        description: "Discover active Redis sessions",
      },
      {
        name: "decrement_scores",
        label: "Decrement Scores",
        description: "Reduce activation by decay rate",
      },
      {
        name: "evict_expired",
        label: "Evict Expired",
        description: "Remove nodes at zero activation",
      },
    ],
  },
  salience: {
    label: "Salience Recompute",
    description: "Recalculates salience scores for all entity nodes",
    schedule: "Every 1hr",
    stages: [
      {
        name: "fetch_entities",
        label: "Fetch Entities",
        description: "Load all entity IDs from Neo4j",
      },
      {
        name: "fetch_metadata",
        label: "Fetch Metadata",
        description: "Load node metadata from PostgreSQL",
      },
      {
        name: "compute_scores",
        label: "Compute Scores",
        description: "Calculate salience using weighted formula",
      },
      {
        name: "update_scores",
        label: "Update Scores",
        description: "Write updated scores back to M_meta",
      },
    ],
  },
  consolidation: {
    label: "Consolidation",
    description:
      "Promotes, archives, merges, and compresses knowledge nodes",
    schedule: "Weekly",
    stages: [
      {
        name: "promote_validated",
        label: "Promote Validated",
        description: "Upgrade auto-learned knowledge confidence",
      },
      {
        name: "archive_stale",
        label: "Archive Stale",
        description: "Archive low-salience, idle nodes",
      },
      {
        name: "merge_duplicates",
        label: "Merge Duplicates",
        description: "Combine near-duplicate entities",
      },
      {
        name: "compress_versions",
        label: "Compress Versions",
        description: "Shorten long version chains",
      },
      {
        name: "generate_report",
        label: "Generate Report",
        description: "Produce consolidation summary",
      },
    ],
  },
  ingestion: {
    label: "Ingestion",
    description: "Processes documents through Cognee ECL pipeline",
    schedule: "On-demand",
    stages: [
      {
        name: "cognee_add",
        label: "cognee.add()",
        description: "Store raw data in Cognee's data store",
      },
      {
        name: "cognee_cognify",
        label: "cognee.cognify()",
        description: "Extract entities, build knowledge graph",
      },
      {
        name: "meta_init",
        label: "M_meta Init",
        description: "Initialize metadata for new nodes",
      },
    ],
  },
};

function createInitialPipelineState(type: PipelineType): PipelineState {
  const def = PIPELINE_DEFINITIONS[type];
  return {
    type,
    label: def.label,
    description: def.description,
    schedule: def.schedule,
    stages: def.stages.map((s) => ({
      name: s.name,
      label: s.label,
      description: s.description,
      status: "idle" as PipelineStageStatus,
      metrics: {},
      duration_ms: null,
      error: null,
    })),
    lastRunTime: null,
    lastRunResult: {},
    isRunning: false,
  };
}

function reducePipelineEvent(
  state: Record<PipelineType, PipelineState>,
  event: PipelineEvent,
): Record<PipelineType, PipelineState> {
  const pipeline = event.pipeline;
  if (!state[pipeline]) return state;

  const newState = { ...state };
  const pState = { ...newState[pipeline] };
  pState.stages = pState.stages.map((s) => ({ ...s }));

  if (event.stage === "__pipeline__") {
    if (event.status === "started") {
      pState.isRunning = true;
      // Reset all stages to idle
      pState.stages = pState.stages.map((s) => ({
        ...s,
        status: "idle" as PipelineStageStatus,
        metrics: {},
        duration_ms: null,
        error: null,
      }));
    } else if (event.status === "completed") {
      pState.isRunning = false;
      pState.lastRunTime = event.timestamp;
      pState.lastRunResult = event.metrics;
    }
  } else {
    // Stage-level event
    const stageIdx = event.stage_index;
    if (stageIdx >= 0 && stageIdx < pState.stages.length) {
      let mappedStatus: PipelineStageStatus = "idle";
      if (event.status === "running") mappedStatus = "running";
      else if (event.status === "completed") mappedStatus = "completed";
      else if (event.status === "failed") mappedStatus = "failed";

      pState.stages[stageIdx] = {
        ...pState.stages[stageIdx],
        status: mappedStatus,
        metrics: { ...pState.stages[stageIdx].metrics, ...event.metrics },
        duration_ms: event.duration_ms ?? pState.stages[stageIdx].duration_ms,
        error: event.error,
      };
    }
    pState.isRunning = true;
  }

  newState[pipeline] = pState;
  return newState;
}

const PIPELINE_TYPES: PipelineType[] = [
  "decay",
  "salience",
  "consolidation",
  "ingestion",
];

function createInitialState(): Record<PipelineType, PipelineState> {
  const state = {} as Record<PipelineType, PipelineState>;
  for (const type of PIPELINE_TYPES) {
    state[type] = createInitialPipelineState(type);
  }
  return state;
}

export function usePipelineStream() {
  const [pipelines, setPipelines] = useState(createInitialState);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setConnected(true);
    setError(null);

    connectPipelineStream(
      {
        onEvent: (event) => {
          setPipelines((prev) => reducePipelineEvent(prev, event));
        },
        onHeartbeat: () => {
          setConnected(true);
          setError(null);
        },
        onError: (msg) => {
          setError(msg);
        },
        onDisconnect: () => {
          setConnected(false);
          // Auto-reconnect after 3 seconds
          reconnectTimerRef.current = setTimeout(connect, 3000);
        },
      },
      controller.signal,
    );
  }, []);

  useEffect(() => {
    // Fetch initial snapshot, then connect SSE
    getPipelineStatus()
      .then((snapshot) => {
        for (const [, event] of Object.entries(snapshot.pipelines)) {
          setPipelines((prev) =>
            reducePipelineEvent(prev, event as PipelineEvent),
          );
        }
      })
      .catch(() => {
        // Ignore — SSE will provide live data
      })
      .finally(() => {
        connect();
      });

    return () => {
      if (abortRef.current) abortRef.current.abort();
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    };
  }, [connect]);

  return { pipelines, connected, error };
}
