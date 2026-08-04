import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CategoryDonut } from "./category-donut";

describe("CategoryDonut", () => {
  it("provides an accessible category summary independent of chart colour", () => {
    render(
      <CategoryDonut
        categories={[
          {
            category_id: "groceries",
            name: "Groceries",
            color: "#16A34A",
            amount: "300.00",
            percentage: "75.00",
          },
          {
            category_id: null,
            name: "Uncategorized",
            color: "#6B7280",
            amount: "100.00",
            percentage: "25.00",
          },
        ]}
      />,
    );

    const summary = screen.getByRole("list", { name: "Expense categories" });

    expect(summary).toHaveTextContent("Groceries");
    expect(summary).toHaveTextContent(/300,00/);
    expect(summary).toHaveTextContent("75.00%");
  });
});
