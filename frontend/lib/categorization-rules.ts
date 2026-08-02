import { requestJson } from "./api";

export interface CategorizationRule {
  id: string;
  keyword: string;
  category_id: string;
  category_name: string;
  category_color: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategorizationRuleCreate {
  keyword: string;
  category_id: string;
  enabled: boolean;
}

export interface CategorizationRuleUpdate {
  keyword?: string;
  category_id?: string;
  enabled?: boolean;
}

interface CategorizationRuleListResponse {
  items: CategorizationRule[];
}

export function categorizationRuleQueryKey(userId: string) {
  return ["categorization-rules", userId] as const;
}

export async function listCategorizationRules(): Promise<CategorizationRule[]> {
  return (await requestJson<CategorizationRuleListResponse>("/categorization-rules")).items;
}

export async function createCategorizationRule(
  payload: CategorizationRuleCreate,
): Promise<CategorizationRule> {
  return requestJson<CategorizationRule>("/categorization-rules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateCategorizationRule(
  ruleId: string,
  payload: CategorizationRuleUpdate,
): Promise<CategorizationRule> {
  return requestJson<CategorizationRule>(`/categorization-rules/${ruleId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deleteCategorizationRule(ruleId: string): Promise<void> {
  await requestJson<null>(`/categorization-rules/${ruleId}`, { method: "DELETE" });
}
