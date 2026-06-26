import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NotificationProvider } from "../src/app/notifications";
import { appRoutes } from "../src/routes/router";
import { createTestQueryClient } from "./test-utils";

const draftId = "11111111-1111-4111-8111-111111111111";
const issueId = "22222222-2222-4222-8222-222222222222";

const draft = {
  id: draftId,
  title: "Severe pothole near school gate",
  original_description: "There is a large pothole near the school gate and bikes are slipping.",
  ai_summary: "A large pothole creates a road safety risk near the school entrance.",
  category: "road_damage",
  severity: "high",
  urgency_level: "urgent",
  urgency_reason: "Children and two-wheel riders use this road every day.",
  suggested_department: "Public Works / Road Maintenance",
  safety_risk: "Riders may lose control near the school entrance.",
  citizen_explanation: "Review the structured complaint before publishing.",
  suggested_next_action: "Publish the issue for community verification.",
  location: "Sector 12",
  landmark: "City Public School",
  urgency_note: "Children cross here every morning.",
  image_url: "/api/v1/media/issues/pothole.png",
  expires_at: "2026-06-26T12:00:00Z",
  created_at: "2026-06-26T10:00:00Z",
};

const publicIssue = {
  id: issueId,
  public_reference: "CP-20260626-11111111",
  title: "Severe pothole near school gate",
  original_description: "There is a large pothole near the school gate and bikes are slipping.",
  ai_summary: "A large pothole creates a road safety risk near the school entrance.",
  category: "road_damage",
  severity: "high",
  urgency_level: "urgent",
  urgency_reason: "Children and two-wheel riders use this road every day.",
  suggested_department: "Public Works / Road Maintenance",
  safety_risk: "Riders may lose control near the school entrance.",
  citizen_explanation: "Community members can confirm whether this issue is present.",
  suggested_next_action: "Arrange an on-site road inspection.",
  location: "Sector 12",
  landmark: "City Public School",
  image_url: "/api/v1/media/issues/pothole.png",
  status: "resolved",
  created_at: "2026-06-26T10:05:00Z",
  updated_at: "2026-06-26T11:30:00Z",
  verification_count: 3,
  community_counts: {
    saw_this_too: 3,
    still_unresolved: 1,
    fixed: 0,
    incorrect: 0,
  },
  updates: [
    {
      id: "30000000-0000-4000-8000-000000000001",
      from_status: null,
      to_status: "reported",
      note: "Issue published by a citizen.",
      actor_type: "system",
      created_at: "2026-06-26T10:05:00Z",
    },
    {
      id: "30000000-0000-4000-8000-000000000002",
      from_status: "reported",
      to_status: "community_verified",
      note: "Automatically promoted after three distinct community confirmations.",
      actor_type: "system",
      created_at: "2026-06-26T10:10:00Z",
    },
    {
      id: "30000000-0000-4000-8000-000000000003",
      from_status: "community_verified",
      to_status: "escalated",
      note: "Escalated to Public Works for inspection.",
      actor_type: "admin",
      created_at: "2026-06-26T10:30:00Z",
    },
    {
      id: "30000000-0000-4000-8000-000000000004",
      from_status: "escalated",
      to_status: "in_progress",
      note: "Road repair team assigned.",
      actor_type: "admin",
      created_at: "2026-06-26T11:00:00Z",
    },
    {
      id: "30000000-0000-4000-8000-000000000005",
      from_status: "in_progress",
      to_status: "resolved",
      note: "Pothole filled and road surface reopened.",
      actor_type: "admin",
      created_at: "2026-06-26T11:30:00Z",
    },
  ],
  viewer_actions: [],
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

function routePath(input: RequestInfo | URL): string {
  const raw = input instanceof Request ? input.url : String(input);
  return new URL(raw).pathname;
}

function renderApp(initialPath = "/report") {
  const router = createMemoryRouter(appRoutes, { initialEntries: [initialPath] });

  return {
    router,
    ...render(
      <QueryClientProvider client={createTestQueryClient()}>
        <NotificationProvider>
          <RouterProvider router={router} />
        </NotificationProvider>
      </QueryClientProvider>,
    ),
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("complete product acceptance flow", () => {
  it("reports, publishes, tracks, and renders the resolved public timeline", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL, options?: RequestInit) => {
        const path = routePath(input);
        if (path === "/api/v1/reports/analyze" && options?.method === "POST") {
          return Promise.resolve(jsonResponse(draft, 201));
        }
        if (path === `/api/v1/reports/${draftId}` && !options?.method) {
          return Promise.resolve(jsonResponse(draft));
        }
        if (path === `/api/v1/reports/${draftId}/publish` && options?.method === "POST") {
          return Promise.resolve(
            jsonResponse({
              issue_id: issueId,
              public_reference: "CP-20260626-11111111",
              status: "reported",
              published_at: "2026-06-26T10:05:00Z",
            }),
          );
        }
        if (path === "/api/v1/issues") {
          return Promise.resolve(
            jsonResponse({
              items: [publicIssue],
              page: 1,
              page_size: 12,
              total_items: 1,
              total_pages: 1,
            }),
          );
        }
        if (path === `/api/v1/issues/${issueId}`) {
          return Promise.resolve(jsonResponse(publicIssue));
        }
        return Promise.resolve(jsonResponse({ error: { message: `Unhandled ${path}` } }, 500));
      }),
    );

    renderApp();

    await user.upload(
      screen.getByLabelText("Issue photo"),
      new File(["fake image"], "pothole.png", { type: "image/png" }),
    );
    await user.type(
      screen.getByLabelText("What did you observe?"),
      "There is a large pothole near the school gate and bikes are slipping.",
    );
    await user.type(screen.getByLabelText("Area or location"), "Sector 12");
    await user.type(screen.getByLabelText("Nearby landmark"), "City Public School");
    await user.click(screen.getByRole("button", { name: "Analyze with AI" }));

    expect(await screen.findByRole("heading", { name: "Review before publishing" }))
      .toBeInTheDocument();
    expect(screen.getByText("Severe pothole near school gate")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Submit report" }));
    expect(await screen.findByRole("heading", { name: "Your issue is now trackable." }))
      .toBeInTheDocument();
    expect(screen.getByText("CP-20260626-11111111")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "View public tracker" }));
    expect(await screen.findByRole("link", { name: "Severe pothole near school gate" }))
      .toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Severe pothole near school gate" }));
    expect(await screen.findByRole("heading", { name: "Severe pothole near school gate" }))
      .toBeInTheDocument();
    expect(screen.getByText("Pothole filled and road surface reopened.")).toBeInTheDocument();
    const timeline = screen.getByRole("list", { name: "Public issue status history" });
    expect(within(timeline).getByText("Reported")).toBeInTheDocument();
    expect(within(timeline).getByText("Community verified")).toBeInTheDocument();
    expect(within(timeline).getByText("Escalated")).toBeInTheDocument();
    expect(within(timeline).getByText("In progress")).toBeInTheDocument();
    expect(within(timeline).getByText("Resolved")).toBeInTheDocument();
  });
});
