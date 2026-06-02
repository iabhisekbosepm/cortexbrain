"use client";

import { useState } from "react";
import Link from "next/link";
import { ConfidenceBadge, Badge } from "@/components/ui/badge";
import { ProgressBar } from "@/components/ui/progress-bar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ThinkingTrace } from "@/components/query/thinking-trace";
import { ActivationReplay } from "@/components/query/activation-replay";
import { submitCorrection } from "@/lib/api/correct";
import { getStoredUserId } from "@/lib/api-client";
import { truncate, timeAgo } from "@/lib/utils";
import type { QueryHistoryEntry, SourceReference } from "@/lib/types";

interface QueryDetailPanelProps {
  entry: QueryHistoryEntry;
  onClose: () => void;
}

const ACTIVATION_MODE_LABELS: Record<string, string> = {
  spreading: "Spreading Activation",
  graph_text: "Graph Text Search",
  vector: "Vector Search",
  continuous_learning: "Continuous Learning",
  none: "None",
};

export function QueryDetailPanel({ entry, onClose }: QueryDetailPanelProps) {
  const [correctingNodeId, setCorrectingNodeId] = useState<string | null>(null);
  const insights = entry.insights;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 shrink-0">
        <h3 className="text-sm font-semibold text-gray-900">Response Details</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">
          &times;
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Query */}
        <Section label="Query">
          <p className="text-sm text-gray-700">{entry.query}</p>
        </Section>

        {/* Confidence */}
        <Section label="Confidence">
          <div className="flex items-center gap-3">
            <ConfidenceBadge level={entry.confidence} />
            <div className="flex-1">
              <ProgressBar
                value={entry.confidence_score * 100}
                color={
                  entry.confidence === "high" ? "bg-green-500" :
                  entry.confidence === "medium" ? "bg-yellow-500" :
                  entry.confidence === "conflicted" ? "bg-purple-500" : "bg-red-500"
                }
              />
            </div>
            <span className="text-sm font-mono text-gray-600">{entry.confidence_score.toFixed(3)}</span>
          </div>
        </Section>

        {/* Answer Source */}
        <Section label="Answer Source">
          {entry.auto_learned ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5">
              <div className="flex items-center gap-2 mb-1">
                <svg className="h-4 w-4 text-amber-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span className="text-sm font-semibold text-amber-800">Direct LLM</span>
              </div>
              <p className="text-xs text-amber-700 leading-relaxed">
                Not found in knowledge base. Answered by the LLM using general knowledge and auto-saved for future queries.
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5">
              <div className="flex items-center gap-2 mb-1">
                <svg className="h-4 w-4 text-emerald-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                </svg>
                <span className="text-sm font-semibold text-emerald-800">Knowledge Base</span>
              </div>
              <p className="text-xs text-emerald-700 leading-relaxed">
                Answered from the knowledge graph using spreading activation and {entry.sources.length} source{entry.sources.length !== 1 ? "s" : ""}.
              </p>
            </div>
          )}
        </Section>

        {/* Reasoning Trace (Agent mode) */}
        {entry.steps && entry.steps.length > 0 && (
          <Section label="Reasoning Trace">
            <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2.5">
              <ThinkingTrace steps={entry.steps} isStreaming={false} />
            </div>
          </Section>
        )}

        {/* Generated Images */}
        {entry.images && entry.images.length > 0 && (
          <Section label="Generated Images">
            <div className="space-y-3">
              {entry.images.map((img, i) => (
                <div key={i} className="space-y-1.5">
                  <img
                    src={`data:${img.content_type};base64,${img.b64_data}`}
                    alt={img.prompt}
                    className="w-full rounded-lg border border-gray-200 shadow-sm"
                  />
                  <p className="text-[11px] text-gray-400 italic truncate" title={img.prompt}>
                    {img.prompt}
                  </p>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Query Insights */}
        {insights && insights.total_nodes_activated > 0 && (
          <Section label="Query Insights">
            <div className="rounded-lg border border-copper-200 bg-copper-50 px-3 py-3 space-y-3">
              {/* Stats row */}
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className="bg-copper-100 text-copper-700 border-copper-200">
                  {insights.total_nodes_activated} node{insights.total_nodes_activated !== 1 ? "s" : ""}
                </Badge>
                <Badge className="bg-copper-100 text-copper-700 border-copper-200">
                  {ACTIVATION_MODE_LABELS[insights.activation_mode] || insights.activation_mode}
                </Badge>
              </div>

              {/* Scores grid */}
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-white/60 rounded-md px-2.5 py-2 text-center">
                  <p className="text-sm font-semibold text-copper-900">
                    {insights.max_activation_score.toFixed(1)}
                  </p>
                  <p className="text-[10px] text-copper-600">Max Activation</p>
                </div>
                <div className="bg-white/60 rounded-md px-2.5 py-2 text-center">
                  <p className="text-sm font-semibold text-copper-900">
                    {insights.avg_salience.toFixed(3)}
                  </p>
                  <p className="text-[10px] text-copper-600">Avg Salience</p>
                </div>
              </div>

              {/* Entities */}
              {insights.entities_extracted.length > 0 && (
                <div>
                  <p className="text-[10px] text-copper-600 mb-1.5">Entities Extracted</p>
                  <div className="flex flex-wrap gap-1">
                    {insights.entities_extracted.map((entity, i) => (
                      <span
                        key={i}
                        className="inline-block rounded-full bg-gray-100 border border-gray-200 px-2 py-0.5 text-[11px] text-gray-600"
                      >
                        {truncate(entity, 24)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Section>
        )}

        {/* Activation Replay */}
        {entry.session_id && (
          <Section label="Activation Replay">
            <ActivationReplay sessionId={entry.session_id} />
          </Section>
        )}

        {/* Flags */}
        <Section label="Flags">
          <div className="flex flex-wrap gap-2">
            {entry.fallback ? (
              <Badge className="bg-orange-100 text-orange-700 border-orange-200">Fallback Mode</Badge>
            ) : (
              <Badge className="bg-green-100 text-green-700 border-green-200">Activation Mode</Badge>
            )}
            {entry.auto_learned && (
              <Badge className="bg-amber-100 text-amber-700 border-amber-200">Auto-learned</Badge>
            )}
          </div>
        </Section>

        {/* Tokens */}
        <Section label="Token Usage">
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-lg font-semibold text-gray-900">{entry.tokens_used.input.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Input</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-lg font-semibold text-gray-900">{entry.tokens_used.output.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Output</p>
            </div>
          </div>
        </Section>

        {/* Sources with inline correction */}
        {entry.sources.length > 0 && (
          <Section label={`Sources (${entry.sources.length})`}>
            <div className="space-y-2">
              {entry.sources.map((src, i) => (
                <SourceCard
                  key={i}
                  source={src}
                  isCorrecting={correctingNodeId === src.node_id}
                  onStartCorrect={() => setCorrectingNodeId(src.node_id)}
                  onDoneCorrect={() => setCorrectingNodeId(null)}
                />
              ))}
            </div>
          </Section>
        )}

        {/* Session & Time */}
        <Section label="Metadata">
          <div className="space-y-1.5 text-xs text-gray-500">
            <Row label="Session" value={entry.session_id} mono />
            <Row label="Time" value={timeAgo(entry.timestamp)} />
          </div>
        </Section>
      </div>
    </div>
  );
}

/* --- Source card with correct button + inline form --- */

function SourceCard({
  source,
  isCorrecting,
  onStartCorrect,
  onDoneCorrect,
}: {
  source: SourceReference;
  isCorrecting: boolean;
  onStartCorrect: () => void;
  onDoneCorrect: () => void;
}) {
  const { toast } = useToast();
  const [correctedValue, setCorrectedValue] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [descExpanded, setDescExpanded] = useState(false);
  const [corrected, setCorrected] = useState(false);

  async function handleSubmit() {
    if (!correctedValue.trim()) return;
    setLoading(true);
    try {
      const res = await submitCorrection({
        node_id: source.node_id,
        corrected_value: correctedValue.trim(),
        user_id: getStoredUserId(),
        reason: reason.trim() || undefined,
      });
      toast(`Correction applied to ${truncate(source.source_name, 20)} — v${res.version}`, "success");
      setCorrectedValue("");
      setReason("");
      setCorrected(true);
      onDoneCorrect();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Correction failed", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      {/* Source info row */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <Link
              href={`/nodes/${source.node_id}`}
              className="group min-w-0"
            >
              <p className="font-medium text-sm text-gray-800 group-hover:text-copper-700 truncate">
                {truncate(source.source_name, 32)}
              </p>
            </Link>
            {source.conflicted && (
              <Badge className="bg-purple-100 text-purple-700 border-purple-200 text-[10px] px-1.5 py-0">
                Conflicted
              </Badge>
            )}
          </div>
          <p className="text-[11px] text-gray-400 font-mono truncate">{source.node_id}</p>
        </div>

        <div className="shrink-0 flex items-center gap-2">
          {source.activation_score != null && (
            <span className="text-[11px] font-mono text-copper-600" title="Activation score">
              {source.activation_score.toFixed(1)}
            </span>
          )}

          <div className="w-14">
            <ProgressBar value={source.confidence * 100} color="bg-green-500" />
            <p className="text-[10px] text-gray-400 text-right mt-0.5">{source.confidence.toFixed(2)}</p>
          </div>

          {source.description && (
            <button
              onClick={() => setDescExpanded(!descExpanded)}
              title={descExpanded ? "Collapse description" : "Expand description"}
              className="shrink-0 rounded-md border border-gray-200 p-1 text-gray-400 hover:text-copper-600 hover:border-copper-300 transition-colors"
            >
              <svg
                className={`h-3 w-3 transition-transform ${descExpanded ? "rotate-180" : ""}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}

          {corrected ? (
            <Badge className="bg-green-100 text-green-700 border-green-200 text-[10px] px-1.5 py-0.5">
              Corrected
            </Badge>
          ) : !isCorrecting ? (
            <button
              onClick={onStartCorrect}
              title="Correct this source"
              className="shrink-0 rounded-md border border-gray-200 px-2 py-1 text-[11px] font-medium text-gray-500 hover:text-copper-700 hover:border-copper-300 hover:bg-copper-50 transition-colors"
            >
              Correct
            </button>
          ) : null}
        </div>
      </div>

      {/* Expandable description */}
      {descExpanded && source.description && (
        <div className="border-t border-gray-100 bg-gray-50 px-3 py-2.5">
          <p className="text-xs text-gray-600 leading-relaxed">{source.description}</p>
          {source.description.length >= 200 && (
            <Link
              href={`/nodes/${source.node_id}`}
              className="inline-block mt-1 text-[11px] text-copper-600 hover:text-copper-800"
            >
              Read more &rarr;
            </Link>
          )}
        </div>
      )}

      {/* Inline correction form */}
      {isCorrecting && (
        <div className="border-t border-gray-100 bg-gray-50 px-3 py-3 space-y-2.5">
          <Textarea
            value={correctedValue}
            onChange={(e) => setCorrectedValue(e.target.value)}
            placeholder="Enter the corrected information..."
            rows={3}
            className="text-sm"
          />
          <Input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason for correction (optional)"
            className="text-sm"
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => {
                setCorrectedValue("");
                setReason("");
                onDoneCorrect();
              }}
              className="text-xs px-3 py-1.5"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              loading={loading}
              disabled={!correctedValue.trim()}
              className="text-xs px-3 py-1.5"
            >
              Submit Correction
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

/* --- Helpers --- */

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{label}</p>
      {children}
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between">
      <span>{label}</span>
      <span className={mono ? "font-mono text-[11px] text-gray-600 truncate max-w-[180px]" : "text-gray-600"}>
        {value}
      </span>
    </div>
  );
}
