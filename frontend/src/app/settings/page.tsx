"use client";

import { useState, useEffect } from "react";
import { PageShell } from "@/components/layout/page-shell";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { StatusDot } from "@/components/ui/status-dot";
import { useApiKey } from "@/hooks/use-api-key";
import { useToast } from "@/components/ui/toast";
import { getHealth } from "@/lib/api/health";

export default function SettingsPage() {
  const { apiKey, apiUrl, userId, saveApiKey, saveApiUrl, saveUserId } = useApiKey();
  const { toast } = useToast();

  const [localKey, setLocalKey] = useState(apiKey);
  const [localUrl, setLocalUrl] = useState(apiUrl);
  const [localUserId, setLocalUserId] = useState(userId);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  // Sync initial values from localStorage after mount
  useEffect(() => {
    setLocalKey(apiKey);
    setLocalUrl(apiUrl);
    setLocalUserId(userId);
  }, [apiKey, apiUrl, userId]);

  function handleSave() {
    saveApiKey(localKey);
    saveApiUrl(localUrl);
    saveUserId(localUserId);
    toast("Settings saved", "success");
  }

  async function handleTestConnection() {
    // Save first so the API client uses updated values
    saveApiKey(localKey);
    saveApiUrl(localUrl);
    saveUserId(localUserId);

    setTesting(true);
    setTestResult(null);
    try {
      const health = await getHealth();
      setTestResult(health.status);
      toast(`Connection ${health.status}`, health.status === "healthy" ? "success" : "info");
    } catch (e) {
      setTestResult("error");
      toast(e instanceof Error ? e.message : "Connection failed", "error");
    } finally {
      setTesting(false);
    }
  }

  return (
    <PageShell title="Settings" description="Configure API connection and user identity">
      <div className="max-w-2xl space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>API Connection</CardTitle>
            <CardDescription>Configure how the frontend connects to CortexBrain backend</CardDescription>
          </CardHeader>
          <div className="space-y-4">
            <Input
              label="API Base URL"
              value={localUrl}
              onChange={(e) => setLocalUrl(e.target.value)}
              placeholder="/api/v1"
            />
            <Input
              label="API Key (Bearer Token)"
              type="password"
              value={localKey}
              onChange={(e) => setLocalKey(e.target.value)}
              placeholder="Enter your API key"
            />
            <Input
              label="User ID"
              value={localUserId}
              onChange={(e) => setLocalUserId(e.target.value)}
              placeholder="default-user"
            />
          </div>
        </Card>

        <div className="flex items-center gap-3">
          <Button onClick={handleSave}>Save Settings</Button>
          <Button variant="secondary" onClick={handleTestConnection} loading={testing}>
            Test Connection
          </Button>
          {testResult && (
            <div className="flex items-center gap-2 text-sm">
              <StatusDot status={testResult === "healthy" ? "ok" : testResult === "degraded" ? "degraded" : "error"} />
              <span className="capitalize">{testResult}</span>
            </div>
          )}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>About</CardTitle>
          </CardHeader>
          <div className="text-sm text-gray-600 space-y-1">
            <p><strong>CortexBrain</strong> — Enterprise AI Knowledge System</p>
            <p>MFCA Memory Architecture with spreading activation, versioned corrections, and full audit trails.</p>
            <p className="text-xs text-gray-400 mt-2">All settings are stored locally in your browser.</p>
          </div>
        </Card>
      </div>
    </PageShell>
  );
}
