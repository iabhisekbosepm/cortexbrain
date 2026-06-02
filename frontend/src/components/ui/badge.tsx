"use client";

import { cn } from "@/lib/utils";
import { confidenceColor } from "@/lib/utils";
import type { ConfidenceLevel } from "@/lib/types";

interface BadgeProps {
  children: React.ReactNode;
  className?: string;
}

export function Badge({ children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  return (
    <Badge className={confidenceColor(level)}>
      {level.charAt(0).toUpperCase() + level.slice(1)}
    </Badge>
  );
}
