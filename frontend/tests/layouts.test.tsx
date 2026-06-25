import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppProviders } from "../src/app/providers";
import { appRoutes } from "../src/routes/router";

vi.stubGlobal(
  "fetch",
  vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "alive",
        service: "CivicPulse AI API",
        version: "0.1.0",
      }),
      { headers: { "Content-Type": "application/json" }, status: 200 },
    ),
  ),
);

describe("application route shells", () => {
  it.each([
    ["/", "Your city has problems. Now they can’t disappear.", "Primary navigation"],
    ["/report", "Report a local issue", "Primary navigation"],
    ["/issues", "Public issue tracker", "Primary navigation"],
    ["/admin", "Administrator dashboard", "Admin navigation"],
    ["/admin/issues", "Manage reported issues", "Admin navigation"],
  ])("renders %s in the intended shell", (path, heading, navigation) => {
    const router = createMemoryRouter(appRoutes, { initialEntries: [path] });
    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: navigation })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Skip to main content" })).toBeInTheDocument();
  });
});
