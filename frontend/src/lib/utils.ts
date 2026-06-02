/* Utility functions: date formatting, confidence colors, UUID helpers */

import type { ConfidenceLevel } from "./types";

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "Never";
  const d = new Date(dateStr);
  return d.toLocaleString();
}

export function timeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function confidenceColor(level: ConfidenceLevel): string {
  switch (level) {
    case "high":
      return "bg-green-100 text-green-800 border-green-200";
    case "medium":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "low":
      return "bg-red-100 text-red-800 border-red-200";
    case "conflicted":
      return "bg-purple-100 text-purple-800 border-purple-200";
  }
}

export function confidenceDot(level: ConfidenceLevel): string {
  switch (level) {
    case "high":
      return "bg-green-500";
    case "medium":
      return "bg-yellow-500";
    case "low":
      return "bg-red-500";
    case "conflicted":
      return "bg-purple-500";
  }
}

export function healthStatusColor(status: string): string {
  switch (status) {
    case "ok":
    case "healthy":
      return "bg-green-500";
    case "degraded":
      return "bg-yellow-500";
    case "error":
    case "unhealthy":
      return "bg-red-500";
    default:
      return "bg-gray-400";
  }
}

/** Generate a UUID — works in non-secure contexts (e.g. http://app.cortexbrain.local) */
export function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for non-secure contexts
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export function isValidUUID(str: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str);
}

export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 3) + "...";
}

export function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
