"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { recomputeSalience } from "@/lib/api/debug";

export function SalienceRecomputeButton({ onComplete }: { onComplete?: () => void }) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    setLoading(true);
    try {
      const res = await recomputeSalience();
      toast(`Salience recomputed — ${res.nodes_updated} nodes updated`, "success");
      onComplete?.();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Recompute failed", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button variant="secondary" onClick={handleClick} loading={loading}>
      Recompute Salience
    </Button>
  );
}
