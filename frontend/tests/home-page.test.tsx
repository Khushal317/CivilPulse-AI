import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HomePage } from "../src/pages/HomePage";
import { renderWithProviders } from "./test-utils";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("HomePage", () => {
  it("shows the product story, civic snapshot, and API connectivity", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url =
          typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
        let payload: unknown;
        if (url.includes("/health/live")) {
          payload = {
            status: "ready",
            service: "CivicPulse AI API",
            version: "0.1.0",
          };
        } else if (url.includes("/api/v1/areas")) {
          payload = {
            items: [
              {
                id: "11111111-1111-4111-8111-111111111111",
                name: "Sector 12",
                slug: "civicpulse-city-sector-12",
                city: "CivicPulse City",
                rank: 1,
                status_label: "improving",
                scores: {
                  overall: 70,
                  infrastructure: 68,
                  cleanliness: 76,
                  safety: 64,
                  participation: 91,
                  responsiveness: 60,
                  environment: 72,
                },
                civic_genome: {
                  civic_health_score: 64,
                  community_power_score: 91,
                  confidence_level: "medium",
                  confidence_reason: "This score is based on moderate activity.",
                  score_limit_reasons: [],
                },
                open_issues: 3,
                resolved_this_week: 2,
                active_missions: 1,
                created_at: "2026-06-27T10:00:00Z",
                updated_at: "2026-06-27T10:00:00Z",
              },
            ],
          };
        } else if (url.includes("/api/v1/missions")) {
          payload = {
            items: [
              {
                id: "22222222-2222-4222-8222-222222222222",
                title: "School Road Safety Check",
                mission_type: "verification",
                status: "active",
                area: {
                  id: "11111111-1111-4111-8111-111111111111",
                  name: "Sector 12",
                  slug: "civicpulse-city-sector-12",
                  city: "CivicPulse City",
                },
                goal_description: "Ask residents to verify the school road safely.",
                target_count: 5,
                progress_count: 2,
                category: "road_damage",
                reward: { points: 20, score_key: "safety" },
                ai_reason: "Road safety needs community verification.",
                joined_count: 2,
                expires_at: "2026-07-04T10:00:00Z",
                published_at: "2026-06-27T10:00:00Z",
                completed_at: null,
                created_at: "2026-06-27T10:00:00Z",
                updated_at: "2026-06-27T10:00:00Z",
              },
            ],
          };
        } else if (url.includes("/api/v1/issues")) {
          payload = {
            items: [
              {
                id: "33333333-3333-4333-8333-333333333333",
                public_reference: "CP-20260629-00000001",
                title: "High severity road damage near school",
                category: "road_damage",
                severity: "high",
                location: "Sector 12",
                landmark: "City Public School",
                latitude: null,
                longitude: null,
                image_url: "/api/v1/media/issues/test.jpg",
                status: "reported",
                created_at: "2026-06-29T10:00:00Z",
                updated_at: "2026-06-29T10:00:00Z",
                verification_count: 2,
              },
            ],
            page: 1,
            page_size: 3,
            total_items: 1,
            total_pages: 1,
          };
        } else {
          payload = {};
        }

        return Promise.resolve(
          new Response(JSON.stringify(payload), {
            headers: { "Content-Type": "application/json" },
            status: 200,
          }),
        );
      }),
    );

    renderWithProviders(<HomePage />);

    expect(
      screen.getByRole("heading", {
        name: "Your neighborhood is alive. Help it evolve.",
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Connected")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Report. Verify. Evolve.",
      }),
    ).toBeInTheDocument();
    expect(await screen.findAllByText("Sector 12")).toHaveLength(2);
    expect(screen.getByText("School Road Safety Check")).toBeInTheDocument();
    expect(screen.getByText("High severity road damage near school")).toBeInTheDocument();
    expect(screen.getByText("AI powered by Gemini")).toBeInTheDocument();
    expect(screen.getByText(/Independent transparency tool/i)).toBeInTheDocument();
  });

  it("keeps the landing page usable when snapshot APIs are unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network unavailable")));

    renderWithProviders(<HomePage />);

    expect(
      screen.getByRole("heading", {
        name: "Your neighborhood is alive. Help it evolve.",
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("Gathering signals")).toHaveLength(2);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(
      screen.getByText(
        "Neighborhood rankings will appear once areas have public Civic Genome signals.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Active missions will appear here after admins publish community quests."),
    ).toBeInTheDocument();
  });
});
