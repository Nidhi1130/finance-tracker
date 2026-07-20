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
