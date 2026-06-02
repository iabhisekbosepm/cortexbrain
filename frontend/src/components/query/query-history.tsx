"use client";

import { QueryResult } from "./query-result";
import { EmptyState } from "@/components/ui/empty-state";
import type { QueryHistoryEntry } from "@/lib/types";

interface QueryHistoryProps {
  history: QueryHistoryEntry[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function QueryHistory({ history, selectedId, onSelect }: QueryHistoryProps) {
  if (history.length === 0) {
    return (
      <EmptyState
        title="No queries yet"
        description="Ask CortexBrain a question to get started"
        icon={
          <svg className="h-12 w-12" fill="none" viewBox="0 0 24 24" strokeWidth="1" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
          </svg>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      {history.map((entry) => (
        <QueryResult
          key={entry.id}
          entry={entry}
          selected={selectedId === entry.id}
          onSelect={() => onSelect(entry.id)}
        />
      ))}
    </div>
  );
}
