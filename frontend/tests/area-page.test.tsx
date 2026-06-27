import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NotificationProvider } from "../src/app/notifications";
import { AreaDetailPage } from "../src/features/areas/AreaDetailPage";
import { NeighborhoodArenaPage } from "../src/features/areas/NeighborhoodArenaPage";
import { RankingsPage } from "../src/features/areas/RankingsPage";
import { createTestQueryClient } from "./test-utils";

const area = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "Sector 12",
  slug: "civicpulse-city-sector-12",
  city: "CivicPulse City",
  rank: 1,
  status_label: "improving",
  scores: {
    overall: 70,
    infrastructure: 68,
    cleanliness: 74,
    safety: 66,
    participation: 80,
    responsiveness: 61,
    environment: 72,
  },
  open_issues: 3,
  resolved_this_week: 2,
  active_missions: 0,
  created_at: "2026-06-27T10:00:00Z",
  updated_at: "2026-06-27T10:00:00Z",
};

const areaDetail = {
  ...area,
  total_issues: 5,
  recent_score_events: [
    {
      id: "22222222-2222-4222-8222-222222222222",
      event_type: "issue_published",
      related_issue_id: "33333333-3333-4333-8333-333333333333",
      related_mission_id: null,
      score_key: "infrastructure",
      score_change: -2,
      previous_score: 70,
      new_score: 68,
      reason: "Issue published by a citizen and included in Civic Genome scoring.",
      created_at: "2026-06-27T10:00:00Z",
    },
  ],
  active_issues: [
    {
      id: "33333333-3333-4333-8333-333333333333",
      public_reference: "CP-20260627-00000001",
      title: "Damaged road near school gate",
      category: "road_damage",
      severity: "high",
      status: "community_verified",
      location: "Sector 12",
      landmark: "City School",
      updated_at: "2026-06-27T10:00:00Z",
    },
  ],
};

const safetyLeader = {
  ...area,
  id: "44444444-4444-4444-8444-444444444444",
  name: "Green Park",
  slug: "civicpulse-city-green-park",
  rank: 2,
  scores: {
    ...area.scores,
    overall: 68,
    safety: 95,
  },
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

function renderArena() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <NotificationProvider>
        <MemoryRouter initialEntries={["/neighborhoods"]}>
          <NeighborhoodArenaPage />
        </MemoryRouter>
      </NotificationProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Neighborhood Arena", () => {
  it("renders civic genome area cards", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ items: [area] })));

    renderArena();

    expect(await screen.findByRole("heading", { name: "Sector 12" })).toBeInTheDocument();
    expect(screen.getByLabelText("Civic Health 70 out of 100")).toBeInTheDocument();
    expect(screen.getByText("Rank #1")).toBeInTheDocument();
    expect(screen.getByText("Improving")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View Civic Genome" }))
      .toHaveAttribute("href", "/neighborhoods/civicpulse-city-sector-12");
    expect(screen.getByText("Open issues")).toBeInTheDocument();
    expect(screen.getByText("Resolved this week")).toBeInTheDocument();
  });

  it("renders a civic genome detail page with score events", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(areaDetail)));

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <NotificationProvider>
          <MemoryRouter initialEntries={["/neighborhoods/civicpulse-city-sector-12"]}>
            <Routes>
              <Route element={<AreaDetailPage />} path="/neighborhoods/:slug" />
            </Routes>
          </MemoryRouter>
        </NotificationProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Sector 12" })).toBeInTheDocument();
    expect(screen.getByText(/Civic Genome events/)).toBeInTheDocument();
    expect(screen.getByText("Citizen report published")).toBeInTheDocument();
    expect(screen.getByText(/infrastructure -2/)).toBeInTheDocument();
    expect(screen.getByText("70 → 68")).toBeInTheDocument();
    expect(screen.getByText("5 total reports")).toBeInTheDocument();
    expect(screen.getByText("Issues currently shaping this Civic Genome")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Damaged road near school gate" }))
      .toHaveAttribute("href", "/issues/33333333-3333-4333-8333-333333333333");
    expect(screen.getByText("Missions will appear here after the mission engine is introduced."))
      .toBeInTheDocument();
  });

  it("renders city rankings and sorts by the active ranking tab", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ items: [area, safetyLeader] })),
    );

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <NotificationProvider>
          <MemoryRouter initialEntries={["/rankings"]}>
            <RankingsPage />
          </MemoryRouter>
        </NotificationProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Positive Civic Genome rankings" }))
      .toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Overall leaders" }))
      .toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Safety" }));
    expect(screen.getByRole("heading", { name: "Safety leaders" })).toBeInTheDocument();
    const links = screen.getAllByRole("link");
    expect(links[0]).toHaveTextContent("Green Park");
  });

  it("shows an empty state before areas exist", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ items: [] })));

    renderArena();

    expect(await screen.findByText("No neighborhood profiles yet")).toBeInTheDocument();
  });

  it("shows a recoverable API failure state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            error: {
              code: "request_failed",
              message: "Neighborhood data temporarily unavailable.",
              details: [],
            },
          },
          503,
        ),
      ),
    );

    renderArena();

    expect(
      await screen.findByText("Neighborhood Arena could not be loaded"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
