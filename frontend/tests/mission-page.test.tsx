import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
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
  expires_at: "2026-07-04T10:00:00Z",
  published_at: "2026-06-27T10:00:00Z",
  completed_at: null,
  created_at: "2026-06-27T10:00:00Z",
  updated_at: "2026-06-27T10:00:00Z",
};

const missionDetail = {
  ...mission,
  linked_issue_ids: ["33333333-3333-4333-8333-333333333333"],
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
    expect(screen.getByRole("link", { name: "View Civic Genome" }))
      .toHaveAttribute("href", "/neighborhoods/civicpulse-city-sector-12");
    expect(screen.getByRole("link", { name: "View linked issue" }))
      .toHaveAttribute("href", "/issues/33333333-3333-4333-8333-333333333333");
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
