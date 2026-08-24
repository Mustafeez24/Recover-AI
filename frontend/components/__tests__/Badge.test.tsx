import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PriorityBadge, RiskBadge, StatusBadge } from "../Badge";

describe("PriorityBadge", () => {
  it("renders a formatted label for each priority", () => {
    render(<PriorityBadge priority="high" />);
    expect(screen.getByText("High")).toBeInTheDocument();
  });
});

describe("StatusBadge", () => {
  it("renders every known recovery case status without crashing", () => {
    const statuses = [
      "detected",
      "planned",
      "validated",
      "executing",
      "recovered",
      "failed",
      "escalated",
      "exhausted",
    ];
    for (const status of statuses) {
      const { unmount } = render(<StatusBadge status={status} />);
      expect(screen.getByText(new RegExp(status, "i"))).toBeInTheDocument();
      unmount();
    }
  });
});

describe("RiskBadge", () => {
  it("renders the risk level text as-is", () => {
    render(<RiskBadge risk="HIGH" />);
    expect(screen.getByText("HIGH")).toBeInTheDocument();
  });
});
