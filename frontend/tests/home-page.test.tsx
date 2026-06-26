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
        name: "Report local problems. Verify with your community. Track until resolved.",
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Connected")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Three simple steps, one public trail.",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Independent transparency tool/i)).toBeInTheDocument();
  });
});
