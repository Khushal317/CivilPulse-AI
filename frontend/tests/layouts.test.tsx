import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppProviders } from "../src/app/providers";
import { appRoutes } from "../src/routes/router";
import { createTestQueryClient } from "./test-utils";

vi.stubGlobal(
  "fetch",
  vi.fn().mockImplementation((input: RequestInfo | URL) => {
    const url =
      typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    let payload: unknown;
    if (url.includes("/api/v1/admin/auth/session")) {
      payload = {
        username: "admin",
        expires_at: "2026-06-26T10:00:00Z",
        csrf_token: "csrf-token",
      };
    } else if (url.includes("/api/v1/admin/dashboard")) {
      payload = {
        metrics: {
          total_reports: 0,
          high_severity: 0,
          verified: 0,
          pending: 0,
          resolved: 0,
        },
        category_breakdown: [],
        latest_reports: [],
        priority_issues: [],
      };
    } else if (url.includes("/api/v1/admin/issues")) {
      payload = {
        items: [],
        page: 1,
        page_size: 20,
        total_items: 0,
        total_pages: 0,
      };
    } else if (url.includes("/api/v1/issues")) {
      payload = {
          items: [],
          page: 1,
          page_size: 12,
          total_items: 0,
          total_pages: 0,
      };
    } else {
      payload = {
        status: "alive",
        service: "CivicPulse AI API",
        version: "0.1.0",
      };
    }
    return Promise.resolve(
      new Response(JSON.stringify(payload), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }),
    );
  }),
);

describe("application route shells", () => {
  it.each([
    [
      "/",
      "Report local problems. Verify with your community. Track until resolved.",
      "Primary navigation",
    ],
    ["/report", "Report a local issue", "Primary navigation"],
    ["/issues", "Public issue tracker", "Primary navigation"],
    ["/admin", "Administrator dashboard", "Admin navigation"],
    ["/admin/issues", "Manage reported issues", "Admin navigation"],
  ])("renders %s in the intended shell", async (path, heading, navigation) => {
    const router = createMemoryRouter(appRoutes, { initialEntries: [path] });
    render(
      <AppProviders queryClient={createTestQueryClient()}>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: navigation })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Skip to main content" })).toBeInTheDocument();
  });
});
