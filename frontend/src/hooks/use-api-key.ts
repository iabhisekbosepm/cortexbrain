"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getStoredApiKey,
  getStoredApiUrl,
  getStoredUserId,
  setStoredApiKey,
  setStoredApiUrl,
  setStoredUserId,
} from "@/lib/api-client";

export function useApiKey() {
  const [apiKey, setApiKey] = useState("");
  const [apiUrl, setApiUrl] = useState("/api/v1");
  const [userId, setUserId] = useState("default-user");

  useEffect(() => {
    setApiKey(getStoredApiKey());
    setApiUrl(getStoredApiUrl());
    setUserId(getStoredUserId());
  }, []);

  const saveApiKey = useCallback((key: string) => {
    setStoredApiKey(key);
    setApiKey(key);
  }, []);

  const saveApiUrl = useCallback((url: string) => {
    setStoredApiUrl(url);
    setApiUrl(url);
  }, []);

  const saveUserId = useCallback((id: string) => {
    setStoredUserId(id);
    setUserId(id);
  }, []);

  return { apiKey, apiUrl, userId, saveApiKey, saveApiUrl, saveUserId };
}
