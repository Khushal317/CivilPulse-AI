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
    } else if (url.includes("/api/v1/areas")) {
      if (url.includes("/api/v1/areas/civicpulse-city-sector-12")) {
        payload = {
          id: "11111111-1111-4111-8111-111111111111",
          name: "Sector 12",
          slug: "civicpulse-city-sector-12",
          city: "CivicPulse City",
          rank: 1,
          status_label: "improving",
          scores: {
            overall: 70,
            infrastructure: 70,
            cleanliness: 70,
            safety: 70,
            participation: 70,
            responsiveness: 70,
            environment: 70,
          },
          open_issues: 0,
          resolved_this_week: 0,
          active_missions: 0,
          total_issues: 0,
          recent_score_events: [],
          active_issues: [],
          created_at: "2026-06-27T10:00:00Z",
          updated_at: "2026-06-27T10:00:00Z",
        };
      } else {
        payload = {
          items: [],
        };
      }
    } else if (url.includes("/api/v1/missions")) {
      const mission = {
        id: "22222222-2222-4222-8222-222222222222",
        title: "Verify repaired streetlights",
        mission_type: "verification",
        status: "active",
        area: {
          id: "11111111-1111-4111-8111-111111111111",
          name: "Sector 12",
          slug: "civicpulse-city-sector-12",
          city: "CivicPulse City",
        },
        goal_description: "Ask nearby residents to confirm the streetlights are working.",
        target_count: 5,
        progress_count: 2,
        category: "streetlight",
        reward: { points: 20, score_key: "participation" },
        ai_reason: "Several residents reported lighting issues in this area.",
        expires_at: "2026-07-04T10:00:00Z",
        published_at: "2026-06-27T10:00:00Z",
        completed_at: null,
        created_at: "2026-06-27T10:00:00Z",
        updated_at: "2026-06-27T10:00:00Z",
      };
      if (url.includes("/api/v1/missions/22222222-2222-4222-8222-222222222222")) {
        payload = {
          ...mission,
          linked_issue_ids: [],
        };
      } else {
        payload = {
          items: [mission],
        };
      }
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
    ["/neighborhoods", "Civic Genome profiles for every area", "Primary navigation"],
    ["/neighborhoods/civicpulse-city-sector-12", "Sector 12", "Primary navigation"],
    ["/rankings", "Positive Civic Genome rankings", "Primary navigation"],
    ["/missions", "Useful missions for local civic progress", "Primary navigation"],
    [
      "/missions/22222222-2222-4222-8222-222222222222",
      "Verify repaired streetlights",
      "Primary navigation",
    ],
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
