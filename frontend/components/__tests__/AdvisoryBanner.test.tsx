import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AdvisoryBanner } from "../AdvisoryBanner";

describe("AdvisoryBanner", () => {
  it("always displays the exact required advisory text", () => {
    render(<AdvisoryBanner />);
    expect(
      screen.getByText("Simulated / Advisory Only — No real payments are executed.")
    ).toBeInTheDocument();
  });
});
