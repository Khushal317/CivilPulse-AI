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
import { AdminMissionsPage } from "../src/features/admin/AdminMissionsPage";
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
const missionDraft = {
  id: "55555555-5555-4555-8555-555555555555",
  title: "Verify Sector 12 streetlights",
  mission_type: "verification",
  status: "draft",
  area: {
    id: "66666666-6666-4666-8666-666666666666",
    name: "Sector 12",
    slug: "civicpulse-city-sector-12",
    city: "CivicPulse City",
  },
  goal_description: "Ask residents to safely confirm public streetlights are working.",
  target_count: 5,
  progress_count: 0,
  category: "streetlight",
  reward: { points: 20, score_key: "participation" },
  ai_reason: "A verified streetlight report needs additional safe observations.",
  joined_count: 0,
  expires_at: "2026-07-04T10:00:00Z",
  published_at: null,
  completed_at: null,
  created_at: "2026-06-27T10:00:00Z",
  updated_at: "2026-06-27T10:00:00Z",
  linked_issue_ids: [issueId],
  viewer_actions: [],
};
const activeMission = {
  ...missionDraft,
  id: "77777777-7777-4777-8777-777777777777",
  status: "active",
  progress_count: 2,
  published_at: "2026-06-27T11:00:00Z",
};
const completedMission = {
  ...activeMission,
  id: "88888888-8888-4888-8888-888888888888",
  status: "completed",
  progress_count: 5,
  completed_at: "2026-06-28T11:00:00Z",
};
const expiredMission = {
  ...activeMission,
  id: "99999999-9999-4999-8999-999999999999",
  status: "expired",
};
const missionConsole = {
  drafts: [missionDraft],
  active: [activeMission],
  completed: [completedMission],
  expired: [expiredMission],
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
            <Route element={<AdminMissionsPage />} path="missions" />
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
        if (url.includes("/admin/missions")) return Promise.resolve(jsonResponse(missionConsole));
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
    expect(screen.getByRole("link", { name: "Open mission console" })).toHaveAttribute(
      "href",
      "/admin/missions",
    );
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
        if (url.includes("/admin/missions")) return Promise.resolve(jsonResponse(missionConsole));
        if (url.includes("/issues/duplicates") && options?.method === "POST") {
          expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-token");
          const body =
            typeof options.body === "string"
              ? (JSON.parse(options.body) as Record<string, unknown>)
              : {};
          expect(body).toMatchObject({
            canonical_issue_id: issueId,
            duplicate_issue_ids: ["44444444-4444-4444-8444-444444444444"],
          });
          return Promise.resolve(
            jsonResponse({
              canonical_issue: issueSummary,
              duplicates_marked: [
                {
                  ...issueSummary,
                  id: "44444444-4444-4444-8444-444444444444",
                  public_reference: "CP-20260625-00000002",
                  title: "Road crater near City School",
                  status: "duplicate",
                },
              ],
            }),
          );
        }
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
    await user.click(
      screen.getByRole("button", { name: "Delete duplicates and keep selected" }),
    );
    expect(await screen.findByText("Duplicate reports removed")).toBeInTheDocument();
    expect(
      await screen.findByText("No possible duplicate clusters found."),
    ).toBeInTheDocument();
    expect(screen.getByText("Sector 12 has repeated road safety reports.")).toBeInTheDocument();
    expect(screen.getByText("Prioritize school-zone hazards first.")).toBeInTheDocument();
    expect(screen.getByText("If ignored, riders may be injured.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Copy message" }));

    expect(writeText).toHaveBeenCalledWith(
      "Please inspect CP-20260625-00000001 near City School.",
    );
    expect(await screen.findByText("Message copied")).toBeInTheDocument();
  });

  it("loads the latest operations report without generating a new one", async () => {
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
        if (url.includes("/operations/latest")) {
          expect(options?.method).toBeUndefined();
          return Promise.resolve(jsonResponse(operationsReport));
        }
        if (url.includes("/admin/missions")) return Promise.resolve(jsonResponse(missionConsole));
        if (url.includes("/operations/analyze")) {
          return Promise.resolve(jsonResponse({ error: { message: "Should not analyze" } }, 500));
        }
        return Promise.resolve(jsonResponse({}));
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    renderRoute("/admin");

    expect(await screen.findByRole("heading", { name: "Executive summary" }))
      .toBeInTheDocument();
    expect(screen.getByText("Two active civic issues need administrator attention."))
      .toBeInTheDocument();
    expect(screen.getByText("Latest operations report")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/operations/analyze"),
      expect.anything(),
    );
  });

  it("manages draft and active missions from the admin console", async () => {
    const user = userEvent.setup();
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
        if (url.includes("/api/v1/areas")) {
          return Promise.resolve(
            jsonResponse({
              items: [
                {
                  id: missionDraft.area.id,
                  name: missionDraft.area.name,
                  slug: missionDraft.area.slug,
                  city: missionDraft.area.city,
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
                  civic_genome: {
                    civic_health_score: 70,
                    community_power_score: 70,
                    confidence_level: "medium",
                    confidence_reason: "This score is based on moderate activity.",
                    score_limit_reasons: [],
                  },
                  open_issues: 1,
                  resolved_this_week: 0,
                  active_missions: 1,
                  created_at: "2026-06-27T10:00:00Z",
                  updated_at: "2026-06-27T10:00:00Z",
                },
              ],
            }),
          );
        }
        if (url.includes("/missions/generate") && options?.method === "POST") {
          expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-token");
          return Promise.resolve(
            jsonResponse({
              model_used: "demo-civic-mission-generator-v1",
              created_drafts: [missionDraft],
            }),
          );
        }
        if (
          url.includes(`/missions/${missionDraft.id}`) &&
          options?.method === "DELETE"
        ) {
          expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-token");
          return Promise.resolve(new Response(null, { status: 204 }));
        }
        if (url.includes("/missions/manual/refine") && options?.method === "POST") {
          expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-token");
          const body =
            typeof options.body === "string"
              ? (JSON.parse(options.body) as Record<string, unknown>)
              : {};
          return Promise.resolve(
            jsonResponse({
              ...body,
              title: "Verify Road damage near DMART",
              goal_description:
                "Ask residents to safely confirm road damage near DMART from public space.",
            }),
          );
        }
        if (url.includes("/missions/manual") && options?.method === "POST") {
          expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-token");
          return Promise.resolve(
            jsonResponse({
              ...missionDraft,
              title: "Verify Road damage near DMART",
              status: "active",
              published_at: "2026-06-28T10:00:00Z",
            }),
          );
        }
        if (url.includes(`/missions/${missionDraft.id}/publish`) && options?.method === "POST") {
          expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-token");
          return Promise.resolve(jsonResponse({ ...missionDraft, status: "active" }));
        }
        if (url.includes(`/missions/${activeMission.id}/expire`) && options?.method === "POST") {
          expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-token");
          return Promise.resolve(jsonResponse({ ...activeMission, status: "expired" }));
        }
        if (url.includes(`/missions/${activeMission.id}/complete`) && options?.method === "POST") {
          expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-token");
          return Promise.resolve(jsonResponse(completedMission));
        }
        if (url.includes("/admin/missions")) return Promise.resolve(jsonResponse(missionConsole));
        return Promise.resolve(jsonResponse({}));
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    renderRoute("/admin/missions");

    expect(await screen.findByRole("heading", { name: "Review and publish community missions" }))
      .toBeInTheDocument();
    expect(await screen.findByText("Draft mission review")).toBeInTheDocument();
    expect(screen.getByText("Active missions")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Generate Community Missions" }));
    expect(await screen.findByText("Mission drafts created")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Publish mission" }));
    expect(await screen.findByText("Mission published")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Delete draft" }));
    expect(await screen.findByText("Mission deleted")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Expire mission" }));
    expect(await screen.findByText("Mission expired")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Mark complete" }));
    expect(await screen.findByText("Mission completed")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Mission heading"), "Road damage near DMART");
    await user.selectOptions(screen.getByLabelText("Neighborhood area"), missionDraft.area.id);
    await user.type(
      screen.getByLabelText("Goal description"),
      "Ask residents to safely confirm road damage near DMART.",
    );
    await user.type(
      screen.getByLabelText("Admin reason"),
      "This mission is useful because the road damage needs safe public confirmation.",
    );
    await user.click(screen.getByRole("button", { name: "Refine with AI" }));
    expect(await screen.findByText("Mission refined with AI")).toBeInTheDocument();
    expect(screen.getByLabelText("Mission heading")).toHaveValue(
      "Verify Road damage near DMART",
    );
    await user.click(screen.getByRole("button", { name: "Publish manually" }));
    expect(await screen.findByText("Manual mission published")).toBeInTheDocument();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/admin/missions/${missionDraft.id}/publish`),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/admin/missions/${missionDraft.id}`),
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/admin/missions/${activeMission.id}/expire`),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(`/admin/missions/${activeMission.id}/complete`),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/missions/manual/refine"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/missions/manual"),
      expect.objectContaining({ method: "POST" }),
    );
  }, 10_000);

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
