import { describe, expect, it } from "vitest";

import { formatCurrency, formatLabel, formatPercent } from "../format";

describe("formatCurrency", () => {
  it("formats a number as INR with no decimals", () => {
    expect(formatCurrency(2999)).toContain("2,999");
    expect(formatCurrency(2999)).toContain("₹");
  });

  it("handles zero", () => {
    expect(formatCurrency(0)).toContain("0");
  });
});

describe("formatLabel", () => {
  it("converts snake_case to Title Case", () => {
    expect(formatLabel("retry_payment")).toBe("Retry Payment");
    expect(formatLabel("subscription_failure")).toBe("Subscription Failure");
  });

  it("returns an em dash for null/undefined", () => {
    expect(formatLabel(null)).toBe("—");
    expect(formatLabel(undefined)).toBe("—");
  });

  it("passes through a single word unchanged (capitalized)", () => {
    expect(formatLabel("escalate")).toBe("Escalate");
  });
});

describe("formatPercent", () => {
  it("converts a 0-1 fraction to a rounded percent string", () => {
    expect(formatPercent(0.82)).toBe("82%");
    expect(formatPercent(0)).toBe("0%");
    expect(formatPercent(1)).toBe("100%");
  });
});
