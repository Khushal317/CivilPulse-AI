import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../src/app/providers";
import { AdminDashboardPage } from "../src/features/admin/AdminDashboardPage";
import { AdminIssueDetailPage } from "../src/features/admin/AdminIssueDetailPage";
import { AdminIssuesPage } from "../src/features/admin/AdminIssuesPage";
import { AdminLoginPage } from "../src/features/admin/AdminLoginPage";
import { AdminLayout } from "../src/layouts/AdminLayout";
import { createTestQueryClient } from "./test-utils";

const issueId = "11111111-1111-4111-8111-111111111111";
const session = {
  username: "admin",
  expires_at: "2026-06-26T10:00:00Z",
  csrf_token: "csrf-token",
};
const issueSummary = {
  id: issueId,
  public_reference: "CP-20260625-00000001",
  title: "Pothole near school",
  category: "road_damage",
  severity: "high",
  status: "reported",
  location: "Sector 12",
  landmark: "City School",
  created_at: "2026-06-25T10:00:00Z",
  updated_at: "2026-06-25T10:00:00Z",
  verification_count: 3,
};
const operationsReport = {
  id: "33333333-3333-4333-8333-333333333333",
  generated_at: "2026-06-26T10:30:00Z",
  created_at: "2026-06-26T10:30:00Z",
  total_issues_analyzed: 2,
  model_used: "demo-civic-operations-agent-v1",
  executive_summary: "Two active civic issues need administrator attention.",
  urgent_issues: [
    {
      issue_id: issueId,
      public_reference: "CP-20260625-00000001",
      title: "Pothole near school",
      location: "Sector 12, near City School",
      department: "Public Works",
      severity: "high",
      priority_reason: "High severity and multiple community confirmations.",
      recommended_action: "Inspect and temporarily barricade the area.",
      suggested_time_window: "Within 24 hours",
    },
  ],
  duplicate_clusters: [
    {
      cluster_title: "Possible school-zone road duplicates",
      issues: [
        {
          issue_id: issueId,
          public_reference: "CP-20260625-00000001",
          title: "Pothole near school",
        },
        {
          issue_id: "44444444-4444-4444-8444-444444444444",
          public_reference: "CP-20260625-00000002",
          title: "Road crater near City School",
        },
      ],
      reason: "Both reports describe nearby road damage.",
      recommended_action: "Review together before dispatching duplicate crews.",
    },
  ],
  area_hotspots: [
    {
      area: "Sector 12",
      issue_count: 2,
      main_categories: ["road_damage"],
      risk_level: "high",
      insight: "Sector 12 has repeated road safety reports.",
    },
  ],
  department_priorities: [
    {
      department: "Public Works",
      open_issues: 2,
      high_priority_count: 1,
      recommended_focus: "Prioritize school-zone hazards first.",
    },
  ],
  escalation_messages: [
    {
      department: "Public Works",
      issue_id: issueId,
      public_reference: "CP-20260625-00000001",
      issue_title: "Pothole near school",
      message: "Please inspect CP-20260625-00000001 near City School.",
    },
  ],
  predicted_risks: [
    {
      issue_id: issueId,
      public_reference: "CP-20260625-00000001",
      issue_title: "Pothole near school",
      risk: "If ignored, riders may be injured.",
      risk_level: "high",
      preventive_action: "Barricade and inspect the road surface.",
    },
  ],
  raw_response: {
    executive_summary: "Two active civic issues need administrator attention.",
  },
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

function detail(status = "reported") {
  return {
    ...issueSummary,
    status,
    original_description: "A resident reported a deep pothole near a school.",
    ai_summary: "A road defect creates a public safety risk.",
    urgency_level: "urgent",
    urgency_reason: "Children use this road.",
    suggested_department: "Public Works",
    safety_risk: "Riders may lose control.",
    citizen_explanation: "Administrator review is needed.",
    suggested_next_action: "Arrange an inspection.",
    image_url: "/api/v1/media/issues/one.jpg",
    image_mime: "image/jpeg",
    citizen_name: "Private Citizen",
    citizen_contact: "private@example.com",
    ai_model: "gemini-2.5-flash",
    prompt_version: "civic-report-v1",
    community_counts: {
      saw_this_too: 3,
      still_unresolved: 0,
      fixed: 0,
      incorrect: 0,
    },
    updates: [
      {
        id: "22222222-2222-4222-8222-222222222222",
        from_status: null,
        to_status: "reported",
        note: "Issue published by a citizen.",
        actor_type: "system",
        created_at: "2026-06-25T10:00:00Z",
      },
    ],
  };
}

function LocationProbe() {
  return <output data-testid="current-path">{useLocation().pathname}</output>;
}

function renderRoute(route: string) {
  return render(
    <AppProviders queryClient={createTestQueryClient()}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route element={<AdminLoginPage />} path="/admin/login" />
          <Route element={<AdminLayout />} path="/admin">
            <Route index element={<AdminDashboardPage />} />
            <Route element={<AdminIssuesPage />} path="issues" />
            <Route element={<AdminIssueDetailPage />} path="issues/:issueId" />
          </Route>
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    </AppProviders>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("administrator workflow", () => {
  it("redirects anonymous users to the administrator login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            error: {
              code: "admin_authentication_required",
              message: "Administrator authentication is required.",
              details: [],
            },
          },
          401,
        ),
      ),
    );

    renderRoute("/admin/issues");

    expect(
      await screen.findByRole("heading", { name: "Administrator sign in" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("current-path")).toHaveTextContent("/admin/login");
  });

  it("signs in and displays protected dashboard aggregates", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
        if (url.includes("/auth/session")) {
          return Promise.resolve(
            jsonResponse(
              {
                error: {
                  code: "admin_authentication_required",
                  message: "Authentication required.",
                  details: [],
                },
              },
              401,
            ),
          );
        }
        if (url.includes("/auth/login")) return Promise.resolve(jsonResponse(session));
        if (url.includes("/dashboard")) {
          return Promise.resolve(
            jsonResponse({
              metrics: {
                total_reports: 15,
                high_severity: 8,
                verified: 5,
                pending: 10,
                resolved: 3,
              },
              category_breakdown: [{ category: "road_damage", count: 5 }],
              latest_reports: [issueSummary],
              priority_issues: [issueSummary],
            }),
          );
        }
        if (url.includes("/operations/latest")) return Promise.resolve(jsonResponse(null));
        return Promise.resolve(jsonResponse({}));
      }),
    );
    renderRoute("/admin/login");

    await user.type(screen.getByLabelText("Password"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Sign in securely" }));

    expect(
      await screen.findByRole("heading", { name: "Administrator dashboard" }),
    ).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getAllByText("Pothole near school")).toHaveLength(2);
  });

  it("generates an operations report and copies an escalation draft", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    const fetchMock = vi.fn().mockImplementation(
      (input: RequestInfo | URL, options?: RequestInit) => {
        const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
        if (url.includes("/auth/session")) return Promise.resolve(jsonResponse(session));
        if (url.includes("/dashboard")) {
          return Promise.resolve(
            jsonResponse({
              metrics: {
                total_reports: 15,
                high_severity: 8,
                verified: 5,
                pending: 10,
                resolved: 3,
              },
              category_breakdown: [{ category: "road_damage", count: 5 }],
              latest_reports: [issueSummary],
              priority_issues: [issueSummary],
            }),
          );
        }
        if (url.includes("/operations/latest")) return Promise.resolve(jsonResponse(null));
        if (url.includes("/operations/analyze") && options?.method === "POST") {
          expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-token");
          return Promise.resolve(jsonResponse(operationsReport));
        }
        return Promise.resolve(jsonResponse({}));
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    renderRoute("/admin");

    expect(await screen.findByRole("heading", { name: "Analyze active city issues" }))
      .toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Analyze City Issues" }));

    expect(await screen.findByRole("heading", { name: "Executive summary" }))
      .toBeInTheDocument();
    expect(screen.getByText("Two active civic issues need administrator attention."))
      .toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open issue" })[0]).toHaveAttribute(
      "href",
      `/admin/issues/${issueId}`,
    );
    expect(screen.getByText("Possible school-zone road duplicates")).toBeInTheDocument();
    expect(screen.getByText("Sector 12 has repeated road safety reports.")).toBeInTheDocument();
    expect(screen.getByText("Prioritize school-zone hazards first.")).toBeInTheDocument();
    expect(screen.getByText("If ignored, riders may be injured.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Copy message" }));

    expect(writeText).toHaveBeenCalledWith(
      "Please inspect CP-20260625-00000001 near City School.",
    );
    expect(await screen.findByText("Message copied")).toBeInTheDocument();
  });

  it("shows private details and confirms a rejection with CSRF", async () => {
    const user = userEvent.setup();
    let rejected = false;
    const fetchMock = vi.fn().mockImplementation(
      (input: RequestInfo | URL, options?: RequestInit) => {
        const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
        if (url.includes("/auth/session")) return Promise.resolve(jsonResponse(session));
        if (options?.method === "POST" && url.includes("/status")) {
          expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-token");
          rejected = true;
          return Promise.resolve(jsonResponse(detail("rejected")));
        }
        if (url.includes(`/admin/issues/${issueId}`)) {
          return Promise.resolve(jsonResponse(detail(rejected ? "rejected" : "reported")));
        }
        return Promise.resolve(jsonResponse({}));
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    renderRoute(`/admin/issues/${issueId}`);

    expect(await screen.findByText("private@example.com")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("New status"), "rejected");
    await user.type(
      screen.getByLabelText("Rejection reason"),
      "Duplicate of an existing civic issue.",
    );
    await user.click(screen.getByRole("button", { name: "Update status" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reject issue" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(await screen.findByText("Rejected")).toBeInTheDocument();
  });
});
