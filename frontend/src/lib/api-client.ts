/* Fetch wrapper with Bearer auth from localStorage */

const STORAGE_KEYS = {
  apiKey: "cortexbrain_api_key",
  apiUrl: "cortexbrain_api_url",
  userId: "cortexbrain_user_id",
} as const;

export function getStoredApiKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(STORAGE_KEYS.apiKey) || "";
}

export function getStoredApiUrl(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(STORAGE_KEYS.apiUrl) || "/api/v1";
}

/**
 * Direct backend URL for SSE streaming.
 * Next.js rewrites proxy buffers responses, which breaks SSE real-time streaming.
 * This returns the direct backend URL to bypass the proxy.
 */
export function getDirectApiUrl(): string {
  if (typeof window === "undefined") return "";
  // If user set a custom URL that's already direct (not a relative path), use it
  const stored = localStorage.getItem(STORAGE_KEYS.apiUrl);
  if (stored && !stored.startsWith("/")) return stored;
  // Otherwise use the env var or default to direct backend
  const backendOrigin = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return `${backendOrigin}/api/v1`;
}

export function getStoredUserId(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(STORAGE_KEYS.userId) || "default-user";
}

export function setStoredApiKey(key: string) {
  localStorage.setItem(STORAGE_KEYS.apiKey, key);
}

export function setStoredApiUrl(url: string) {
  localStorage.setItem(STORAGE_KEYS.apiUrl, url);
}

export function setStoredUserId(id: string) {
  localStorage.setItem(STORAGE_KEYS.userId, id);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: unknown,
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const baseUrl = getStoredApiUrl();
  const apiKey = getStoredApiKey();

  const url = `${baseUrl}${path}`;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  // Only set Content-Type for non-FormData bodies
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const text = await res.text();
    let body: unknown = text;
    try {
      body = JSON.parse(text);
    } catch {
      // keep as text
    }
    throw new ApiError(res.status, res.statusText, body);
  }

  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  postForm: <T>(path: string, formData: FormData) =>
    request<T>(path, {
      method: "POST",
      body: formData,
    }),
};
