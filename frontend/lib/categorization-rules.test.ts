import { beforeEach, describe, expect, it, vi } from "vitest";
import { requestJson } from "./api";
import {
  categorizationRuleQueryKey,
  createCategorizationRule,
  deleteCategorizationRule,
  listCategorizationRules,
  updateCategorizationRule,
} from "./categorization-rules";

vi.mock("./api", () => ({
  requestJson: vi.fn(),
}));

const requestJsonMock = vi.mocked(requestJson);

const rule = {
  id: "rule-1",
  keyword: "spotify",
  category_id: "category-1",
  category_name: "Subscriptions",
  category_color: "#7C3AED",
  enabled: true,
  created_at: "2026-08-02T10:00:00Z",
  updated_at: "2026-08-02T10:00:00Z",
};

describe("categorization rule API client", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
  });

  it("scopes the rules cache key to the authenticated user", () => {
    expect(categorizationRuleQueryKey("user-a")).toEqual(["categorization-rules", "user-a"]);
  });

  it("lists rules from the FastAPI endpoint", async () => {
    requestJsonMock.mockResolvedValue({ items: [rule] });

    await expect(listCategorizationRules()).resolves.toEqual([rule]);
    expect(requestJsonMock).toHaveBeenCalledWith("/categorization-rules");
  });

  it("creates a rule with the API field names", async () => {
    requestJsonMock.mockResolvedValue(rule);

    await createCategorizationRule({
      keyword: "spotify",
      category_id: "category-1",
      enabled: true,
    });

    expect(requestJsonMock).toHaveBeenCalledWith("/categorization-rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword: "spotify", category_id: "category-1", enabled: true }),
    });
  });

  it("updates a rule through its FastAPI resource URL", async () => {
    requestJsonMock.mockResolvedValue({ ...rule, enabled: false });

    await updateCategorizationRule("rule-1", { enabled: false });

    expect(requestJsonMock).toHaveBeenCalledWith("/categorization-rules/rule-1", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: false }),
    });
  });

  it("deletes a rule through its FastAPI resource URL", async () => {
    requestJsonMock.mockResolvedValue(null);

    await deleteCategorizationRule("rule-1");

    expect(requestJsonMock).toHaveBeenCalledWith("/categorization-rules/rule-1", {
      method: "DELETE",
    });
  });
});
