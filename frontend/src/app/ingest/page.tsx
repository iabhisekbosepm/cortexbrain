"use client";

import { useState, useCallback, useRef } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { FileUploadZone } from "@/components/ingest/file-upload-zone";
import { IngestForm } from "@/components/ingest/ingest-form";
import { BatchStatusCard } from "@/components/ingest/batch-status-card";
import { IngestHistory, type IngestHistoryItem } from "@/components/ingest/ingest-history";
import { PipelinePanel, type PipelineStep, type PipelineStepStatus } from "@/components/ingest/pipeline-panel";
import { generateId } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { ingestSync, ingestBatch, ingestText, ingestTextAsync } from "@/lib/api/ingest";

const PIPELINE_STEPS = [
  { id: "upload", label: "Upload Files", description: "Sending files to the CortexBrain server" },
  { id: "add", label: "Cognee Add", description: "Ingesting data into Cognee's data store" },
  { id: "cognify", label: "Build Knowledge Graph", description: "Extracting entities, relationships, and building the graph" },
  { id: "meta", label: "Initialize Metadata", description: "Computing salience scores and creating M_meta entries" },
];

function makeSteps(activeId?: string, error?: boolean): PipelineStep[] {
  let passedActive = false;
  return PIPELINE_STEPS.map((s) => {
    if (error && s.id === activeId) {
      passedActive = true;
      return { ...s, status: "error" as PipelineStepStatus };
    }
    if (s.id === activeId) {
      passedActive = true;
      return { ...s, status: "active" as PipelineStepStatus };
    }
    if (!passedActive && activeId) {
      return { ...s, status: "completed" as PipelineStepStatus };
    }
    return { ...s, status: "pending" as PipelineStepStatus };
  });
}

export default function IngestPage() {
  const { toast } = useToast();
  const [inputMode, setInputMode] = useState<"file" | "text">("file");
  const [files, setFiles] = useState<File[]>([]);
  const [rawText, setRawText] = useState("");
  const [pastedImages, setPastedImages] = useState<File[]>([]);
  const [datasetName, setDatasetName] = useState("default");
  const [sourceType, setSourceType] = useState("document");
  const [mode, setMode] = useState<"sync" | "batch">("sync");
  const [loading, setLoading] = useState(false);
  const [activeBatchIds, setActiveBatchIds] = useState<string[]>([]);
  const [history, setHistory] = useState<IngestHistoryItem[]>([]);

  // Pipeline state
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>(makeSteps());
  const [pipelineResult, setPipelineResult] = useState<{
    dataset: string;
    nodesInitialized: number;
    files: string[];
  } | null>(null);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const stepTimers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = useCallback(() => {
    stepTimers.current.forEach(clearTimeout);
    stepTimers.current = [];
  }, []);

  function handlePaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    const items = e.clipboardData?.items;
    if (!items) return;

    const imageFiles: File[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) {
          // Generate a meaningful filename from the mime type
          const ext = item.type.split("/")[1]?.replace("jpeg", "jpg") || "png";
          const named = new File([file], `pasted-image-${Date.now()}-${i}.${ext}`, {
            type: item.type,
          });
          imageFiles.push(named);
        }
      }
    }

    if (imageFiles.length > 0) {
      e.preventDefault();
      setPastedImages((prev) => [...prev, ...imageFiles]);
      toast(`${imageFiles.length} image(s) pasted`, "info");
    }
  }

  function removePastedImage(index: number) {
    setPastedImages((prev) => prev.filter((_, i) => i !== index));
  }

  /** Check if text mode has images — if so, route through file upload path */
  const hasImages = pastedImages.length > 0;
  const hasTextContent = rawText.trim().length > 0;

  async function handleSubmit() {
    if (inputMode === "file" && files.length === 0) return;
    if (inputMode === "text" && !hasTextContent && !hasImages) return;

    setLoading(true);
    setPipelineResult(null);
    setPipelineError(null);

    // Start pipeline animation
    setPipelineSteps(makeSteps("upload"));

    try {
      if (inputMode === "text" && !hasImages) {
        // Pure text ingestion (no images) — use JSON text endpoint
        if (mode === "sync") {
          clearTimers();
          stepTimers.current.push(
            setTimeout(() => setPipelineSteps(makeSteps("add")), 500),
          );
          stepTimers.current.push(
            setTimeout(() => setPipelineSteps(makeSteps("cognify")), 1500),
          );

          const res = await ingestText(rawText, datasetName, sourceType);

          clearTimers();
          setPipelineSteps(makeSteps("meta"));
          await new Promise((r) => setTimeout(r, 500));

          setPipelineSteps(
            PIPELINE_STEPS.map((s) => ({ ...s, status: "completed" as PipelineStepStatus })),
          );
          setPipelineResult({
            dataset: datasetName,
            nodesInitialized: res.nodes_initialized || 0,
            files: ["(pasted text)"],
          });

          toast(
            `Text ingested — ${res.nodes_initialized || 0} nodes created`,
            "success",
          );
          setHistory((prev) => [
            {
              id: generateId(),
              files: [`Text (${rawText.length} chars)`],
              mode: "sync",
              status: res.status,
              dataset: datasetName,
              nodesInitialized: res.nodes_initialized,
              timestamp: new Date(),
            },
            ...prev,
          ]);
        } else {
          const res = await ingestTextAsync(rawText, datasetName);

          clearTimers();
          setPipelineSteps(
            PIPELINE_STEPS.map((s, i) =>
              i === 0
                ? { ...s, status: "completed" as PipelineStepStatus }
                : {
                    ...s,
                    status: "pending" as PipelineStepStatus,
                    description:
                      i === 1 ? "Queued as background Celery task" : s.description,
                  },
            ),
          );
          setPipelineResult({
            dataset: res.dataset,
            nodesInitialized: 0,
            files: ["(pasted text)"],
          });

          toast(`Batch text task queued: ${res.task_id.slice(0, 8)}...`, "info");
          setActiveBatchIds((prev) => [res.task_id, ...prev]);
          setHistory((prev) => [
            {
              id: generateId(),
              files: [`Text (${rawText.length} chars)`],
              mode: "batch",
              status: res.status,
              dataset: res.dataset,
              taskId: res.task_id,
              timestamp: new Date(),
            },
            ...prev,
          ]);
        }
        setRawText("");
      } else if (inputMode === "text" && hasImages) {
        // Mixed text + images — convert text to .txt blob, combine, use file path
        const allFiles: File[] = [...pastedImages];
        const fileLabels: string[] = pastedImages.map((f) => f.name);

        if (hasTextContent) {
          const textBlob = new File(
            [rawText],
            `pasted-text-${Date.now()}.txt`,
            { type: "text/plain" },
          );
          allFiles.unshift(textBlob);
          fileLabels.unshift(`Text (${rawText.length} chars)`);
        }

        if (mode === "sync") {
          clearTimers();
          stepTimers.current.push(
            setTimeout(() => setPipelineSteps(makeSteps("add")), 800),
          );
          stepTimers.current.push(
            setTimeout(() => setPipelineSteps(makeSteps("cognify")), 2500),
          );

          const res = await ingestSync(allFiles, datasetName, sourceType);

          clearTimers();
          setPipelineSteps(makeSteps("meta"));
          await new Promise((r) => setTimeout(r, 500));

          setPipelineSteps(
            PIPELINE_STEPS.map((s) => ({ ...s, status: "completed" as PipelineStepStatus })),
          );
          setPipelineResult({
            dataset: datasetName,
            nodesInitialized: res.nodes_initialized || 0,
            files: res.files || fileLabels,
          });

          toast(
            `Ingested ${allFiles.length} item(s) — ${res.nodes_initialized || 0} nodes`,
            "success",
          );
          setHistory((prev) => [
            {
              id: generateId(),
              files: res.files || fileLabels,
              mode: "sync",
              status: res.status,
              dataset: datasetName,
              nodesInitialized: res.nodes_initialized,
              timestamp: new Date(),
            },
            ...prev,
          ]);
        } else {
          const res = await ingestBatch(allFiles, datasetName);

          clearTimers();
          setPipelineSteps(
            PIPELINE_STEPS.map((s, i) =>
              i === 0
                ? { ...s, status: "completed" as PipelineStepStatus }
                : {
                    ...s,
                    status: "pending" as PipelineStepStatus,
                    description:
                      i === 1 ? "Queued as background Celery task" : s.description,
                  },
            ),
          );
          setPipelineResult({
            dataset: res.dataset,
            nodesInitialized: 0,
            files: res.files || fileLabels,
          });

          toast(`Batch task queued: ${res.task_id.slice(0, 8)}...`, "info");
          setActiveBatchIds((prev) => [res.task_id, ...prev]);
          setHistory((prev) => [
            {
              id: generateId(),
              files: res.files || fileLabels,
              mode: "batch",
              status: res.status,
              dataset: res.dataset,
              taskId: res.task_id,
              timestamp: new Date(),
            },
            ...prev,
          ]);
        }
        setRawText("");
        setPastedImages([]);
      } else {
        // File ingestion (existing logic)
        if (mode === "sync") {
          clearTimers();
          stepTimers.current.push(
            setTimeout(() => setPipelineSteps(makeSteps("add")), 800),
          );
          stepTimers.current.push(
            setTimeout(() => setPipelineSteps(makeSteps("cognify")), 2500),
          );

          const res = await ingestSync(files, datasetName, sourceType);

          clearTimers();
          setPipelineSteps(makeSteps("meta"));
          await new Promise((r) => setTimeout(r, 500));

          setPipelineSteps(
            PIPELINE_STEPS.map((s) => ({ ...s, status: "completed" as PipelineStepStatus })),
          );
          setPipelineResult({
            dataset: datasetName,
            nodesInitialized: res.nodes_initialized || 0,
            files: res.files || files.map((f) => f.name),
          });

          toast(
            `Ingested ${res.files?.length || 0} file(s) — ${res.nodes_initialized || 0} nodes`,
            "success",
          );
          setHistory((prev) => [
            {
              id: generateId(),
              files: res.files || files.map((f) => f.name),
              mode: "sync",
              status: res.status,
              dataset: datasetName,
              nodesInitialized: res.nodes_initialized,
              timestamp: new Date(),
            },
            ...prev,
          ]);
        } else {
          const res = await ingestBatch(files, datasetName);

          clearTimers();
          setPipelineSteps(
            PIPELINE_STEPS.map((s, i) =>
              i === 0
                ? { ...s, status: "completed" as PipelineStepStatus }
                : {
                    ...s,
                    status: "pending" as PipelineStepStatus,
                    description:
                      i === 1 ? "Queued as background Celery task" : s.description,
                  },
            ),
          );
          setPipelineResult({
            dataset: res.dataset,
            nodesInitialized: 0,
            files: res.files || files.map((f) => f.name),
          });

          toast(`Batch task queued: ${res.task_id.slice(0, 8)}...`, "info");
          setActiveBatchIds((prev) => [res.task_id, ...prev]);
          setHistory((prev) => [
            {
              id: generateId(),
              files: res.files || files.map((f) => f.name),
              mode: "batch",
              status: res.status,
              dataset: res.dataset,
              taskId: res.task_id,
              timestamp: new Date(),
            },
            ...prev,
          ]);
        }
        setFiles([]);
      }
    } catch (e) {
      clearTimers();
      const errMsg = e instanceof Error ? e.message : "Ingestion failed";
      setPipelineSteps((prev) => {
        const activeStep = prev.find((s) => s.status === "active");
        return makeSteps(activeStep?.id || "upload", true);
      });
      setPipelineError(errMsg);
      toast(errMsg, "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageShell
      title="Document Ingestion"
      description="Upload documents and images to build the knowledge graph"
    >
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left column: Upload + Settings */}
        <div className="lg:col-span-3 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Input Source</CardTitle>
            </CardHeader>
            {/* Tab toggle */}
            <div className="flex gap-1 rounded-lg bg-gray-100 p-1 mb-4">
              <button
                type="button"
                onClick={() => setInputMode("file")}
                className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  inputMode === "file"
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Upload Files
              </button>
              <button
                type="button"
                onClick={() => setInputMode("text")}
                className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  inputMode === "text"
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Paste Text
              </button>
            </div>

            {inputMode === "file" ? (
              <FileUploadZone
                files={files}
                onFilesChange={setFiles}
                onSizeError={(name) => toast(`${name} exceeds 20 MB limit`, "error")}
              />
            ) : (
              <div>
                <textarea
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  onPaste={handlePaste}
                  placeholder="Paste or type text here. You can also paste images from your clipboard (Ctrl+V / Cmd+V)."
                  rows={8}
                  className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder:text-gray-400 focus:border-copper-500 focus:outline-none focus:ring-1 focus:ring-copper-500 resize-y"
                />
                {rawText.length > 0 && (
                  <p className="mt-2 text-xs text-gray-500">
                    {rawText.length.toLocaleString()} characters
                  </p>
                )}

                {/* Pasted image previews */}
                {pastedImages.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-medium text-gray-600">
                      Pasted Images ({pastedImages.length})
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {pastedImages.map((img, i) => (
                        <div
                          key={i}
                          className="relative group rounded-lg border border-gray-200 overflow-hidden"
                        >
                          <img
                            src={URL.createObjectURL(img)}
                            alt={img.name}
                            className="h-20 w-20 object-cover"
                          />
                          <button
                            type="button"
                            onClick={() => removePastedImage(i)}
                            className="absolute top-0.5 right-0.5 h-5 w-5 rounded-full bg-black/60 text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            &times;
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Ingestion Settings</CardTitle>
            </CardHeader>
            <IngestForm
              datasetName={datasetName}
              onDatasetNameChange={setDatasetName}
              sourceType={sourceType}
              onSourceTypeChange={setSourceType}
              mode={mode}
              onModeChange={setMode}
              onSubmit={handleSubmit}
              loading={loading}
              fileCount={files.length}
              inputMode={inputMode}
              hasText={hasTextContent}
              pastedImageCount={pastedImages.length}
            />
          </Card>

          {activeBatchIds.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-gray-700">
                Active Batch Tasks
              </h3>
              {activeBatchIds.map((id) => (
                <BatchStatusCard key={id} taskId={id} />
              ))}
            </div>
          )}

          <IngestHistory items={history} />
        </div>

        {/* Right column: Pipeline visualization */}
        <div className="lg:col-span-2">
          <div className="lg:sticky lg:top-6">
            <PipelinePanel
              steps={pipelineSteps}
              result={pipelineResult}
              error={pipelineError}
            />
          </div>
        </div>
      </div>
    </PageShell>
  );
}
