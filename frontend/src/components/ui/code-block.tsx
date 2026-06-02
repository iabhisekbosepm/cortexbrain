"use client";

import { cn } from "@/lib/utils";

interface CodeBlockProps {
  children: string;
  className?: string;
}

export function CodeBlock({ children, className }: CodeBlockProps) {
  return (
    <pre
      className={cn(
        "overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100 font-mono",
        className,
      )}
    >
      <code>{children}</code>
    </pre>
  );
}
