"use client";

import { useState, useEffect, useCallback } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { ReviewQueue } from "@/components/review/review-queue";
import { getReviewQueue } from "@/lib/api/review";
import type { ReviewQueueResponse } from "@/lib/types";

export default function ReviewPage() {
  const [data, setData] = useState<ReviewQueueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getReviewQueue();
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load review queue");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  return (
    <PageShell
      title="Validation Queue"
      description="Review auto-learned knowledge nodes — approve to promote, reject to archive"
      actions={
        <Button variant="secondary" onClick={loadQueue} loading={loading}>
          Refresh
        </Button>
      }
    >
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700 mb-6">
          {error}
        </div>
      )}

      {loading && !data && (
        <div className="flex justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      )}

      {data && data.total === 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <div className="text-gray-400 mb-2">
            <svg className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" strokeWidth="1" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
            </svg>
          </div>
          <p className="text-lg font-medium text-gray-700">No nodes pending review</p>
          <p className="text-sm text-gray-400 mt-1">
            All auto-learned knowledge has been validated. New items will appear as the system learns.
          </p>
        </div>
      )}

      {data && data.total > 0 && (
        <>
          <p className="text-sm text-gray-500 mb-4">
            {data.total} node{data.total !== 1 ? "s" : ""} pending review
          </p>
          <ReviewQueue nodes={data.nodes} onAction={loadQueue} />
        </>
      )}
    </PageShell>
  );
}
