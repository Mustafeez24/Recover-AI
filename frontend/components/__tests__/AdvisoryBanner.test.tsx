import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AdvisoryBanner } from "../AdvisoryBanner";

describe("AdvisoryBanner", () => {
  it("always displays the simulation mode label and safety disclosure", () => {
    render(<AdvisoryBanner />);
    expect(screen.getByText("Simulation Mode")).toBeInTheDocument();
    expect(
      screen.getByText(/All recovery actions are advisory and simulated\. No real payments are executed\./)
    ).toBeInTheDocument();
  });
});
