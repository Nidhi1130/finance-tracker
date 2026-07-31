import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CashFlowChart } from "./cash-flow-chart";

describe("CashFlowChart", () => {
  it("provides every period's income and expense in an accessible data table", () => {
    render(
      <CashFlowChart
        points={[
          {
            period_start: "2026-07-01",
            label: "1 Jul",
            income: "1200.50",
            expense: "300.00",
          },
          {
            period_start: "2026-07-02",
            label: "2 Jul",
            income: "0.00",
            expense: "125.25",
          },
        ]}
      />,
    );

    const table = screen.getByRole("table", { name: "Cash flow data" });

    expect(within(table).getByText("1 Jul")).toBeInTheDocument();
    expect(within(table).getByText("2 Jul")).toBeInTheDocument();
    expect(within(table).getByText(/1\s200,50/)).toBeInTheDocument();
    expect(within(table).getByText(/300,00/)).toBeInTheDocument();
    expect(within(table).getByText(/125,25/)).toBeInTheDocument();

    const secondPeriodRow = within(table).getByRole("row", { name: /2 Jul/ });
    const [secondPeriodIncome] = within(secondPeriodRow).getAllByRole("cell");

    expect(secondPeriodIncome).toHaveTextContent(/0,00/);
  });
});
