import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

let browserSupabaseClient:
  | ReturnType<typeof createClient>
  | null = null;

export function hasSupabaseConfig(): boolean {
  return Boolean(supabaseUrl && supabaseAnonKey);
}

export function getSupabaseBrowserClient() {
  if (!hasSupabaseConfig()) {
    throw new Error("Supabase is not configured");
  }

  if (!browserSupabaseClient) {
    browserSupabaseClient = createClient(supabaseUrl as string, supabaseAnonKey as string);
  }

  return browserSupabaseClient;
}
