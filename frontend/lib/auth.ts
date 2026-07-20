import { hasSupabaseConfig, getSupabaseBrowserClient } from "./supabase";

const fallbackUserId = "00000000-0000-0000-0000-000000000001";

function toBase64Url(value: string): string {
  return btoa(value).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function buildUnsignedJwt(userId: string): string {
  const header = toBase64Url(JSON.stringify({ alg: "none", typ: "JWT" }));
  const payload = toBase64Url(JSON.stringify({ sub: userId }));
  return `${header}.${payload}.signature`;
}

export async function getApiAuthToken(): Promise<string | null> {
  if (hasSupabaseConfig()) {
    const supabase = getSupabaseBrowserClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }

  return process.env.NEXT_PUBLIC_DEV_AUTH_TOKEN ?? buildUnsignedJwt(fallbackUserId);
}

export async function buildAuthHeaders(
  headers: HeadersInit = {},
): Promise<Headers> {
  const merged = new Headers(headers);
  const token = await getApiAuthToken();
  if (token) {
    merged.set("Authorization", `Bearer ${token}`);
  }
  return merged;
}
