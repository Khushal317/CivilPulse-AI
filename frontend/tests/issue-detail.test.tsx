import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NotificationProvider } from "../src/app/notifications";
import { IssueDetailPage } from "../src/features/issues/IssueDetailPage";
import { createTestQueryClient } from "./test-utils";

const issueId = "11111111-1111-4111-8111-111111111111";

function detail(overrides: Record<string, unknown> = {}) {
  return {
    id: issueId,
    public_reference: "CP-20260625-00000001",
    title: "Deep pothole beside the school crossing",
    original_description: "A deep pothole is causing riders to swerve near the school gate.",
    ai_summary: "A damaged road surface creates a safety risk near a school crossing.",
    category: "road_damage",
    severity: "high",
    urgency_level: "urgent",
    urgency_reason: "Children and riders use this road every day.",
    suggested_department: "Public Works",
    safety_risk: "Two-wheel riders may lose control.",
    citizen_explanation: "Community members can confirm whether this issue is present.",
    suggested_next_action: "Arrange an on-site road inspection.",
    location: "Sector 12",
    landmark: "City Public School",
    image_url: "/api/v1/media/issues/pothole.jpg",
    status: "reported",
    created_at: "2026-06-25T10:00:00Z",
    updated_at: "2026-06-25T10:00:00Z",
    verification_count: 2,
    community_counts: {
      saw_this_too: 2,
      still_unresolved: 1,
      fixed: 0,
      incorrect: 0,
    },
    updates: [
      {
        id: "22222222-2222-4222-8222-222222222222",
        from_status: null,
        to_status: "reported",
        note: "Issue reported by a citizen.",
        actor_type: "system",
        created_at: "2026-06-25T10:00:00Z",
      },
    ],
    viewer_actions: [],
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

function renderDetail() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <NotificationProvider>
        <MemoryRouter initialEntries={[`/issues/${issueId}`]}>
          <Routes>
            <Route element={<IssueDetailPage />} path="/issues/:issueId" />
          </Routes>
        </MemoryRouter>
      </NotificationProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("issue details and community signals", () => {
  it("renders the complete public issue and chronological timeline", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(detail())));
    renderDetail();

    expect(
      await screen.findByRole("heading", {
        name: "Deep pothole beside the school crossing",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("CP-20260625-00000001")).toBeInTheDocument();
    expect(screen.getByText("A deep pothole is causing riders to swerve near the school gate."))
      .toBeInTheDocument();
    expect(screen.getByText("A damaged road surface creates a safety risk near a school crossing."))
      .toBeInTheDocument();
    expect(screen.getByText("Issue reported by a citizen.")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Public issue status history" })).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAttribute(
      "src",
      "http://localhost:8000/api/v1/media/issues/pothole.jpg",
    );
  });

  it("records a confirmation, promotes status, and marks the signal submitted", async () => {
    const user = userEvent.setup();
    let promoted = false;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((_input: RequestInfo | URL, options?: RequestInit) => {
        if (options?.method === "POST") {
          promoted = true;
          return Promise.resolve(
            jsonResponse({
              action_type: "saw_this_too",
              accepted: true,
              issue_status: "community_verified",
              community_counts: {
                saw_this_too: 3,
                still_unresolved: 1,
                fixed: 0,
                incorrect: 0,
              },
              viewer_actions: ["saw_this_too"],
            }),
          );
        }
        return Promise.resolve(
          jsonResponse(
            detail(
              promoted
                ? {
                    status: "community_verified",
                    verification_count: 3,
                    community_counts: {
                      saw_this_too: 3,
                      still_unresolved: 1,
                      fixed: 0,
                      incorrect: 0,
                    },
                    viewer_actions: ["saw_this_too"],
                  }
                : {},
            ),
          ),
        );
      }),
    );
    renderDetail();

    const actionLabel = await screen.findByText("I saw this too");
    const actionRow = actionLabel.closest<HTMLElement>(".community-action");
    expect(actionRow).not.toBeNull();
    await user.click(within(actionRow!).getByRole("button", { name: "Add signal" }));

    expect(await within(actionRow!).findByRole("button", { name: "Submitted" })).toBeDisabled();
    expect(await screen.findByText("Community verified")).toBeInTheDocument();
    expect(within(actionRow!).getByText("3")).toBeInTheDocument();
  });

  it("keeps every community action unavailable for rejected issues", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(detail({ status: "rejected" }))),
    );
    renderDetail();

    expect(
      await screen.findByText(
        "Community signals are unavailable because this issue was rejected.",
      ),
    ).toBeInTheDocument();
    for (const button of screen.getAllByRole("button", { name: "Add signal" })) {
      expect(button).toBeDisabled();
    }
  });
});
