"use client";

import { StatusDot } from "@/components/ui/status-dot";

interface ConnectionStatusProps {
  connected: boolean;
  error: string | null;
}

export function ConnectionStatus({ connected, error }: ConnectionStatusProps) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <StatusDot
        status={connected ? "healthy" : "error"}
        pulse={connected}
        size="sm"
      />
      <span className={connected ? "text-green-600" : "text-red-500"}>
        {connected ? "Live" : "Disconnected"}
      </span>
      {error && (
        <span className="text-xs text-red-400 ml-1 truncate max-w-[200px]">
          ({error})
        </span>
      )}
    </div>
  );
}
