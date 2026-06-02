"use client";

import { useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { submitCorrection } from "@/lib/api/correct";
import { getStoredUserId } from "@/lib/api-client";

interface CorrectionFormProps {
  nodeId: string;
  open: boolean;
  onClose: () => void;
  onCorrected: () => void;
}

export function CorrectionForm({ nodeId, open, onClose, onCorrected }: CorrectionFormProps) {
  const { toast } = useToast();
  const [correctedValue, setCorrectedValue] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!correctedValue.trim()) return;

    setLoading(true);
    try {
      const res = await submitCorrection({
        node_id: nodeId,
        corrected_value: correctedValue.trim(),
        user_id: getStoredUserId(),
        reason: reason.trim() || undefined,
      });
      toast(`Correction applied — v${res.version}`, "success");
      setCorrectedValue("");
      setReason("");
      onCorrected();
      onClose();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Correction failed", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Submit Correction">
      <form onSubmit={handleSubmit} className="space-y-4">
        <p className="text-xs text-gray-500 font-mono">{nodeId}</p>
        <Textarea
          label="Corrected Value"
          value={correctedValue}
          onChange={(e) => setCorrectedValue(e.target.value)}
          placeholder="Enter the correct information..."
          rows={4}
          required
        />
        <Input
          label="Reason (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Why is this correction needed?"
        />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Submit Correction
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
