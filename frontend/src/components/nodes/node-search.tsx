"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { isValidUUID } from "@/lib/utils";

export function NodeSearch() {
  const [nodeId, setNodeId] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  function handleSearch() {
    const trimmed = nodeId.trim();
    if (!trimmed) return;
    if (!isValidUUID(trimmed)) {
      setError("Invalid UUID format");
      return;
    }
    setError("");
    router.push(`/nodes/${trimmed}`);
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <div className="flex-1">
          <Input
            value={nodeId}
            onChange={(e) => {
              setNodeId(e.target.value);
              setError("");
            }}
            placeholder="Enter node UUID (e.g., 550e8400-e29b-41d4-a716-446655440000)"
            className="font-mono text-sm"
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <Button onClick={handleSearch}>Lookup</Button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
