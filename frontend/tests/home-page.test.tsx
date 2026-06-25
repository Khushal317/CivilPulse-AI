import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HomePage } from "../src/pages/HomePage";
import { renderWithProviders } from "./test-utils";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("HomePage", () => {
  it("shows the product message and reports API connectivity", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: "ready",
            service: "CivicPulse AI API",
            version: "0.1.0",
          }),
      }),
    );

    renderWithProviders(<HomePage />);

    expect(
      screen.getByRole("heading", {
        name: "Your city has problems. Now they can’t disappear.",
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Connected · v0.1.0")).toBeInTheDocument();
    expect(screen.getByText("Phase 4 · AI-assisted reporting")).toBeInTheDocument();
  });
});
