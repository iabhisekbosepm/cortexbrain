"use client";

import { useState, useEffect, useCallback } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { TimelineSummaryCards } from "@/components/timeline/timeline-summary";
import { TimelineFilters } from "@/components/timeline/timeline-filters";
import { TimelineEventList } from "@/components/timeline/timeline-event-list";
import { getTimeline } from "@/lib/api/timeline";
import type { TimelineResponse } from "@/lib/types";

const PAGE_SIZE = 30;

export default function TimelinePage() {
  const [data, setData] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [action, setAction] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [offset, setOffset] = useState(0);

  const loadTimeline = useCallback(async (append = false) => {
    if (append) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const currentOffset = append ? offset : 0;
      const result = await getTimeline({
        action: action || undefined,
        start: startDate || undefined,
        end: endDate || undefined,
        limit: PAGE_SIZE,
        offset: currentOffset,
      });

      if (append && data) {
        setData({
          ...result,
          events: [...data.events, ...result.events],
        });
      } else {
        setData(result);
      }

      if (!append) setOffset(PAGE_SIZE);
      else setOffset(currentOffset + PAGE_SIZE);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load timeline");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [action, startDate, endDate, offset, data]);

  // Reset and reload when filters change
  useEffect(() => {
    setOffset(0);
    setData(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action, startDate, endDate]);

  // Load data when filters or reset happens
  useEffect(() => {
    if (data === null) {
      loadTimeline(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const handleClearFilters = () => {
    setAction("");
    setStartDate("");
    setEndDate("");
  };

  return (
    <PageShell
      title="Meta Memory Timeline"
      description="Chronological audit trail of all PostgreSQL events — corrections, ingestions, decay cycles, and consolidation runs"
      actions={
        <Button variant="secondary" onClick={() => { setData(null); }} loading={loading}>
          Refresh
        </Button>
      }
    >
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700 mb-6">
          {error}
        </div>
      )}

      {/* Summary cards */}
      {data && (
        <div className="mb-6">
          <TimelineSummaryCards summary={data.summary} />
        </div>
      )}

      {/* Filters */}
      <div className="mb-6">
        <TimelineFilters
          action={action}
          onActionChange={setAction}
          startDate={startDate}
          onStartChange={setStartDate}
          endDate={endDate}
          onEndChange={setEndDate}
          onClear={handleClearFilters}
        />
      </div>

      {/* Loading state */}
      {loading && !data && (
        <div className="flex justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {/* Event list */}
      {data && (
        <>
          <TimelineEventList events={data.events} />

          {/* Load more */}
          {data.has_more && (
            <div className="flex justify-center mt-8">
              <Button
                variant="secondary"
                onClick={() => loadTimeline(true)}
                loading={loadingMore}
              >
                Load More Events
              </Button>
            </div>
          )}

          {/* Event count footer */}
          <p className="text-center text-xs text-gray-400 mt-4">
            Showing {data.events.length} of {data.summary.total_events} events
          </p>
        </>
      )}
    </PageShell>
  );
}
