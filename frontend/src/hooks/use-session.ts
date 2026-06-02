"use client";

import { useState, useCallback } from "react";
import { generateId } from "@/lib/utils";

export function useSession() {
  const [sessionId, setSessionId] = useState(() => generateId());

  const newSession = useCallback(() => {
    const id = generateId();
    setSessionId(id);
    return id;
  }, []);

  return { sessionId, setSessionId, newSession };
}
