"use client";

import { cn } from "@/lib/utils";

const ACTION_OPTIONS = [
  { value: "", label: "All Events" },
  { value: "correction", label: "Corrections" },
  { value: "ingestion", label: "Ingestions" },
  { value: "decay", label: "Decays" },
  { value: "consolidation", label: "Consolidations" },
  { value: "continuous_learning", label: "Auto-learned" },
];

interface TimelineFiltersProps {
  action: string;
  onActionChange: (action: string) => void;
  startDate: string;
  onStartChange: (date: string) => void;
  endDate: string;
  onEndChange: (date: string) => void;
  onClear: () => void;
}

export function TimelineFilters({
  action,
  onActionChange,
  startDate,
  onStartChange,
  endDate,
  onEndChange,
  onClear,
}: TimelineFiltersProps) {
  const hasFilters = action || startDate || endDate;

  return (
    <div className="flex flex-wrap items-end gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      {/* Action filter chips */}
      <div className="flex-1 min-w-[200px]">
        <label className="block text-xs font-medium text-gray-500 mb-2">Action Type</label>
        <div className="flex flex-wrap gap-1.5">
          {ACTION_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onActionChange(opt.value)}
              className={cn(
                "rounded-full px-3 py-1 text-xs font-medium border transition-colors",
                action === opt.value
                  ? "bg-copper-600 text-white border-copper-600"
                  : "bg-white text-gray-600 border-gray-300 hover:border-copper-400 hover:text-copper-700",
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Date range */}
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-2">From</label>
        <input
          type="date"
          value={startDate}
          onChange={(e) => onStartChange(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-copper-500 focus:border-copper-500"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-2">To</label>
        <input
          type="date"
          value={endDate}
          onChange={(e) => onEndChange(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-copper-500 focus:border-copper-500"
        />
      </div>

      {hasFilters && (
        <button
          onClick={onClear}
          className="text-xs text-gray-500 hover:text-copper-600 underline pb-1"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
