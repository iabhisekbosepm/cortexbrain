"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { formatDate, truncate, cn } from "@/lib/utils";
import type { AuditLogEntry } from "@/lib/types";

const actionConfig: Record<string, { color: string; dotColor: string; icon: string; label: string }> = {
  correction: {
    color: "bg-copper-100 text-copper-800 border-copper-200",
    dotColor: "bg-copper-600",
    icon: "pencil",
    label: "Correction",
  },
  ingestion: {
    color: "bg-blue-100 text-blue-800 border-blue-200",
    dotColor: "bg-blue-500",
    icon: "arrow-up",
    label: "Ingestion",
  },
  decay: {
    color: "bg-amber-100 text-amber-800 border-amber-200",
    dotColor: "bg-amber-500",
    icon: "clock",
    label: "Decay",
  },
  consolidation: {
    color: "bg-purple-100 text-purple-800 border-purple-200",
    dotColor: "bg-purple-500",
    icon: "merge",
    label: "Consolidation",
  },
  continuous_learning: {
    color: "bg-green-100 text-green-800 border-green-200",
    dotColor: "bg-green-500",
    icon: "learn",
    label: "Auto-learned",
  },
};

function getActionStyle(action: string) {
  // Match consolidation subtypes (consolidation:merge, consolidation:summary)
  if (action.startsWith("consolidation")) {
    const sub = action.includes(":") ? action.split(":")[1] : "";
    const base = actionConfig["consolidation"];
    return { ...base, label: sub ? `Consolidation (${sub})` : base.label };
  }
  return actionConfig[action] || {
    color: "bg-gray-100 text-gray-700 border-gray-200",
    dotColor: "bg-gray-400",
    icon: "dot",
    label: action,
  };
}

/** Group events by date (YYYY-MM-DD) */
function groupByDate(events: AuditLogEntry[]): Map<string, AuditLogEntry[]> {
  const groups = new Map<string, AuditLogEntry[]>();
  for (const event of events) {
    const dateKey = event.timestamp ? event.timestamp.split("T")[0] : "Unknown";
    if (!groups.has(dateKey)) groups.set(dateKey, []);
    groups.get(dateKey)!.push(event);
  }
  return groups;
}

function formatDateHeader(dateStr: string): string {
  if (dateStr === "Unknown") return dateStr;
  const date = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date.getTime() === today.getTime()) return "Today";
  if (date.getTime() === yesterday.getTime()) return "Yesterday";
  return date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}

function ActionIcon({ action, className }: { action: string; className?: string }) {
  const iconClass = cn("h-4 w-4", className);
  switch (action) {
    case "correction":
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" />
        </svg>
      );
    case "ingestion":
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
        </svg>
      );
    case "decay":
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
        </svg>
      );
    case "consolidation":
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
        </svg>
      );
    case "continuous_learning":
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
      );
    default:
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <circle cx="12" cy="12" r="3" />
        </svg>
      );
  }
}

function formatTime(timestamp: string): string {
  if (!timestamp) return "";
  const d = new Date(timestamp);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function TimelineEventList({ events }: { events: AuditLogEntry[] }) {
  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
        <div className="text-gray-400 mb-2">
          <svg className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" strokeWidth="1" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
        </div>
        <p className="text-sm text-gray-500">No events found.</p>
        <p className="text-xs text-gray-400 mt-1">Events will appear here as the system processes queries, corrections, and maintenance tasks.</p>
      </div>
    );
  }

  const grouped = groupByDate(events);

  return (
    <div className="space-y-8">
      {Array.from(grouped.entries()).map(([dateKey, dayEvents]) => (
        <div key={dateKey}>
          {/* Date header */}
          <div className="flex items-center gap-3 mb-4">
            <h3 className="text-sm font-semibold text-gray-700">{formatDateHeader(dateKey)}</h3>
            <div className="flex-1 h-px bg-gray-200" />
            <span className="text-xs text-gray-400">
              {dayEvents.length} event{dayEvents.length !== 1 ? "s" : ""}
            </span>
          </div>

          {/* Timeline */}
          <div className="relative ml-4">
            {/* Vertical line */}
            <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gray-200" />

            {dayEvents.map((event, i) => {
              const style = getActionStyle(event.action);
              return (
                <div key={event.id} className="relative pl-8 pb-6 last:pb-0 group">
                  {/* Timeline dot */}
                  <div
                    className={cn(
                      "absolute left-0 top-1.5 h-3 w-3 rounded-full -translate-x-[5px] ring-2 ring-white transition-transform group-hover:scale-125",
                      style.dotColor,
                    )}
                  />

                  {/* Event card */}
                  <div className="rounded-lg border border-gray-100 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <div className={cn("rounded-md p-1.5", style.color.split(" ")[0])}>
                          <ActionIcon action={event.action} className={style.color.split(" ")[1]} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <Badge className={style.color}>{style.label}</Badge>
                            <span className="text-xs text-gray-400">v{event.version}</span>
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">
                            by <span className="font-medium text-gray-700">{event.changed_by}</span>
                          </p>
                        </div>
                      </div>
                      <span className="text-xs text-gray-400 whitespace-nowrap shrink-0">
                        {formatTime(event.timestamp)}
                      </span>
                    </div>

                    {/* Values diff */}
                    {(event.previous_value || event.new_value) && (
                      <div className="mt-3 space-y-1.5">
                        {event.previous_value && (
                          <div className="flex items-start gap-2">
                            <span className="text-xs text-red-400 font-mono mt-0.5 shrink-0">-</span>
                            <p className="text-xs text-gray-500 bg-red-50 rounded px-2 py-1 font-mono">
                              {truncate(event.previous_value, 150)}
                            </p>
                          </div>
                        )}
                        {event.new_value && (
                          <div className="flex items-start gap-2">
                            <span className="text-xs text-green-500 font-mono mt-0.5 shrink-0">+</span>
                            <p className="text-xs text-gray-700 bg-green-50 rounded px-2 py-1 font-mono">
                              {truncate(event.new_value, 150)}
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Reason */}
                    {event.reason && (
                      <p className="mt-2 text-xs text-gray-500 italic">
                        {truncate(event.reason, 200)}
                      </p>
                    )}

                    {/* Node link */}
                    <div className="mt-2 pt-2 border-t border-gray-50">
                      <Link
                        href={`/nodes/${event.node_id}`}
                        className="text-xs text-copper-600 hover:text-copper-700 hover:underline font-mono"
                      >
                        {event.node_id}
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
