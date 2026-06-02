"use client";

import { cn, healthStatusColor } from "@/lib/utils";

interface StatusDotProps {
  status: string;
  pulse?: boolean;
  size?: "sm" | "md";
}

export function StatusDot({ status, pulse = true, size = "md" }: StatusDotProps) {
  const sizeClass = size === "sm" ? "h-2 w-2" : "h-3 w-3";
  return (
    <span
      className={cn(
        "inline-block rounded-full",
        sizeClass,
        healthStatusColor(status),
        pulse && "animate-pulse-dot",
      )}
    />
  );
}
