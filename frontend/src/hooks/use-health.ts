"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getHealth } from "@/lib/api/health";
import type { HealthResponse, HealthHistoryEntry } from "@/lib/types";

export function useHealth(enabled = true, intervalMs = 10000) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HealthHistoryEntry[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getHealth();
      setHealth(data);
      setHistory((prev) => {
        const entry: HealthHistoryEntry = {
          timestamp: new Date(),
          status: data.status,
          services: {
            redis: data.redis.status,
            neo4j: data.neo4j.status,
            qdrant: data.qdrant.status,
            postgres: data.postgres.status,
            llm: data.llm.status,
          },
        };
        return [entry, ...prev].slice(0, 20);
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Health check failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    refresh();
    intervalRef.current = setInterval(refresh, intervalMs);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [enabled, intervalMs, refresh]);

  return { health, loading, error, history, refresh };
}
