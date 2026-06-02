"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getBatchStatus } from "@/lib/api/ingest";
import type { BatchStatusResponse } from "@/lib/types";

export function useBatchStatus(taskId: string | null, intervalMs = 3000) {
  const [status, setStatus] = useState<BatchStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = useCallback(async () => {
    if (!taskId) return;
    try {
      const data = await getBatchStatus(taskId);
      setStatus(data);
      // Stop polling on terminal states
      if (data.status === "SUCCESS" || data.status === "FAILURE") {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Poll failed");
    }
  }, [taskId]);

  useEffect(() => {
    if (!taskId) return;
    setStatus(null);
    setError(null);
    poll();
    intervalRef.current = setInterval(poll, intervalMs);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [taskId, intervalMs, poll]);

  return { status, error };
}
