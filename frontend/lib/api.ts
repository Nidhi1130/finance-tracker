import { buildAuthHeaders } from "./auth";

const defaultApiBaseUrl = "http://localhost:8000";

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? defaultApiBaseUrl;
}

export function buildApiUrl(path: string): string {
  return `${getApiBaseUrl()}${path}`;
}

export async function buildApiHeaders(headers: HeadersInit = {}): Promise<Headers> {
  return buildAuthHeaders(headers);
}

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await buildApiHeaders(init?.headers);
  const response = await fetch(buildApiUrl(path), { ...init, headers });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const body = (await response.json()) as ApiErrorBody;
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((item) => item.msg).filter(Boolean).join(", ") || message;
      }
    } catch {
      const text = await response.text();
      message = text || message;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null as T;
  }

  return (await response.json()) as T;
}
