import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NotificationProvider } from "../src/app/notifications";
import { MissionDetailPage } from "../src/features/missions/MissionDetailPage";
import { MissionsPage } from "../src/features/missions/MissionsPage";
import { createTestQueryClient } from "./test-utils";

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
  joined_count: 4,
  expires_at: "2026-07-04T10:00:00Z",
  published_at: "2026-06-27T10:00:00Z",
  completed_at: null,
  created_at: "2026-06-27T10:00:00Z",
  updated_at: "2026-06-27T10:00:00Z",
};

const missionDetail = {
  ...mission,
  linked_issue_ids: ["33333333-3333-4333-8333-333333333333"],
  viewer_actions: [],
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Community Missions", () => {
  it("renders active mission cards", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ items: [mission] })));

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <NotificationProvider>
          <MemoryRouter initialEntries={["/missions"]}>
            <MissionsPage />
          </MemoryRouter>
        </NotificationProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Verify repaired streetlights" }))
      .toBeInTheDocument();
    expect(screen.getByText("2/5 progress")).toBeInTheDocument();
    expect(screen.getByText("4 joined")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sector 12" }))
      .toHaveAttribute("href", "/neighborhoods/civicpulse-city-sector-12");
    expect(screen.getByRole("link", { name: "View mission" }))
      .toHaveAttribute("href", "/missions/22222222-2222-4222-8222-222222222222");
  });

  it("renders mission detail shell", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(missionDetail)));

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <NotificationProvider>
          <MemoryRouter initialEntries={["/missions/22222222-2222-4222-8222-222222222222"]}>
            <Routes>
              <Route element={<MissionDetailPage />} path="/missions/:missionId" />
            </Routes>
          </MemoryRouter>
        </NotificationProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Verify repaired streetlights" }))
      .toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "2/5 actions completed" }))
      .toBeInTheDocument();
    expect(screen.getByText("20 participation points when completed")).toBeInTheDocument();
    expect(screen.getByText("4 citizen(s) joined this mission.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View Civic Genome" }))
      .toHaveAttribute("href", "/neighborhoods/civicpulse-city-sector-12");
    expect(screen.getByRole("link", { name: "View linked issue" }))
      .toHaveAttribute("href", "/issues/33333333-3333-4333-8333-333333333333");
  });

  it("submits mission participation actions and updates progress", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL, options?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      if (url.includes("/actions") && options?.method === "POST") {
        const body = JSON.parse(options.body as string) as {
          action_type: string;
          issue_id: string | null;
        };
        expect(body.action_type).toBe("verified_issue");
        expect(body.issue_id).toBe("33333333-3333-4333-8333-333333333333");
        return Promise.resolve(
          jsonResponse({
            action_type: "verified_issue",
            accepted: true,
            mission_status: "active",
            progress_count: 3,
            target_count: 5,
            joined_count: 4,
            viewer_actions: ["verified_issue"],
          }),
        );
      }
      return Promise.resolve(jsonResponse(missionDetail));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <NotificationProvider>
          <MemoryRouter initialEntries={["/missions/22222222-2222-4222-8222-222222222222"]}>
            <Routes>
              <Route element={<MissionDetailPage />} path="/missions/:missionId" />
            </Routes>
          </MemoryRouter>
        </NotificationProvider>
      </QueryClientProvider>,
    );

    await screen.findByRole("heading", { name: "Verify repaired streetlights" });
    await user.click(screen.getByRole("button", { name: "Verify linked issue" }));

    expect(await screen.findByText("Mission action recorded")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "3/5 actions completed" }))
      .toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Recorded" })).toBeDisabled();
  });

  it("shows a positive empty state when no missions are active", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ items: [] })));

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <NotificationProvider>
          <MemoryRouter initialEntries={["/missions"]}>
            <MissionsPage />
          </MemoryRouter>
        </NotificationProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("No active missions yet")).toBeInTheDocument();
  });
});
