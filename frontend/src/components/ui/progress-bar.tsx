"use client";

import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number; // 0 to 100
  className?: string;
  color?: string;
}

export function ProgressBar({ value, className, color = "bg-copper-600" }: ProgressBarProps) {
  return (
    <div className={cn("h-2 w-full rounded-full bg-gray-200 overflow-hidden", className)}>
      <div
        className={cn("h-full rounded-full transition-all duration-300", color)}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
