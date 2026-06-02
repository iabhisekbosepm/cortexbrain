"use client";

import Link from "next/link";
import type { SourceReference } from "@/lib/types";
import { truncate } from "@/lib/utils";

export function SourceList({ sources }: { sources: SourceReference[] }) {
  if (sources.length === 0) return null;

  return (
    <div>
      <p className="text-xs font-medium text-gray-500 mb-2">Sources ({sources.length})</p>
      <div className="flex flex-wrap gap-2">
        {sources.map((src, i) => (
          <Link
            key={i}
            href={`/nodes/${src.node_id}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs hover:bg-copper-50 hover:border-copper-200 transition-colors"
          >
            <span className="font-medium text-gray-800">{truncate(src.source_name, 30)}</span>
            <span className="text-gray-400 font-mono text-[10px]">{src.confidence.toFixed(2)}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
