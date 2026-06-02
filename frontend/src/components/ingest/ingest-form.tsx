"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface IngestFormProps {
  datasetName: string;
  onDatasetNameChange: (name: string) => void;
  sourceType: string;
  onSourceTypeChange: (type: string) => void;
  mode: "sync" | "batch";
  onModeChange: (mode: "sync" | "batch") => void;
  onSubmit: () => void;
  loading: boolean;
  fileCount: number;
  inputMode: "file" | "text";
  hasText: boolean;
  pastedImageCount?: number;
}

export function IngestForm({
  datasetName,
  onDatasetNameChange,
  sourceType,
  onSourceTypeChange,
  mode,
  onModeChange,
  onSubmit,
  loading,
  fileCount,
  inputMode,
  hasText,
  pastedImageCount = 0,
}: IngestFormProps) {
  const canSubmitText = hasText || pastedImageCount > 0;

  function getButtonLabel() {
    if (loading) return "Processing...";
    if (inputMode === "file") {
      return `Ingest ${fileCount} file${fileCount !== 1 ? "s" : ""}`;
    }
    if (pastedImageCount > 0 && hasText) {
      return `Ingest Text & ${pastedImageCount} Image${pastedImageCount !== 1 ? "s" : ""}`;
    }
    if (pastedImageCount > 0) {
      return `Ingest ${pastedImageCount} Image${pastedImageCount !== 1 ? "s" : ""}`;
    }
    return "Ingest Text";
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Dataset Name"
          value={datasetName}
          onChange={(e) => onDatasetNameChange(e.target.value)}
          placeholder="default"
        />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Source Type</label>
          <select
            value={sourceType}
            onChange={(e) => onSourceTypeChange(e.target.value)}
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-copper-500 focus:outline-none focus:ring-1 focus:ring-copper-500"
          >
            <option value="document">Document</option>
            <option value="slack">Slack</option>
            <option value="git">Git</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Processing Mode</label>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => onModeChange("sync")}
            className={`flex-1 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
              mode === "sync"
                ? "border-copper-600 bg-copper-50 text-copper-700"
                : "border-gray-300 bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            <span className="block font-semibold">Synchronous</span>
            <span className="text-xs opacity-70">Wait for completion</span>
          </button>
          <button
            type="button"
            onClick={() => onModeChange("batch")}
            className={`flex-1 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
              mode === "batch"
                ? "border-copper-600 bg-copper-50 text-copper-700"
                : "border-gray-300 bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            <span className="block font-semibold">Batch (Async)</span>
            <span className="text-xs opacity-70">Background Celery task</span>
          </button>
        </div>
      </div>

      <Button
        onClick={onSubmit}
        loading={loading}
        disabled={inputMode === "file" ? fileCount === 0 : !canSubmitText}
      >
        {getButtonLabel()}
      </Button>
    </div>
  );
}
