import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HomePage } from "../src/pages/HomePage";

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

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const router = createMemoryRouter([{ path: "/", element: <HomePage /> }]);

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("heading", {
        name: "Your city has problems. Now they can’t disappear.",
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Connected · v0.1.0")).toBeInTheDocument();
  });
});
