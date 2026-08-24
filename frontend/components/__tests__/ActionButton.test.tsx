import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ActionButton } from "../ActionButton";

describe("ActionButton", () => {
  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    render(
      <ActionButton onClick={onClick} isPending={false}>
        Execute
      </ActionButton>
    );
    fireEvent.click(screen.getByText("Execute"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("disables itself and shows the pending label while pending", () => {
    const onClick = vi.fn();
    render(
      <ActionButton onClick={onClick} isPending pendingLabel="Executing…">
        Execute
      </ActionButton>
    );
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(screen.getByText("Executing…")).toBeInTheDocument();
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});
