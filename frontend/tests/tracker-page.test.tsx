import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NotificationProvider } from "../src/app/notifications";
import { TrackerPage } from "../src/features/issues/TrackerPage";
import { createTestQueryClient } from "./test-utils";

const issue = {
  id: "11111111-1111-4111-8111-111111111111",
  public_reference: "CP-20260625-00000001",
  title: "Broken streetlight near community park",
  category: "streetlight",
  severity: "high",
  location: "Green Park",
  landmark: "Community playground",
  latitude: 26.9124,
  longitude: 75.7873,
  image_url: "/api/v1/media/issues/streetlight.jpg",
  status: "in_progress",
  created_at: "2026-06-25T10:00:00Z",
  updated_at: "2026-06-25T10:00:00Z",
  verification_count: 4,
};

const mapIssue = {
  id: issue.id,
  public_reference: issue.public_reference,
  title: issue.title,
  category: issue.category,
  severity: issue.severity,
  status: issue.status,
  location: issue.location,
  landmark: issue.landmark,
  neighborhood: "Green Park",
  latitude: 26.9124,
  longitude: 75.7873,
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

function trackerResponse(overrides: Record<string, unknown> = {}) {
  return {
    items: [issue],
    page: 1,
    page_size: 12,
    total_items: 1,
    total_pages: 1,
    ...overrides,
  };
}

function mapResponse(overrides: Record<string, unknown> = {}) {
  return {
    items: [mapIssue],
    total_items: 1,
    unmapped_items: 0,
    ...overrides,
  };
}

function routePath(input: RequestInfo | URL): string {
  const raw = input instanceof Request ? input.url : String(input);
  return new URL(raw).pathname;
}

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="current-search">{location.search}</output>;
}

function renderTracker(route: string) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <NotificationProvider>
        <MemoryRouter initialEntries={[route]}>
          <TrackerPage />
          <LocationProbe />
        </MemoryRouter>
      </NotificationProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("public tracker", () => {
  it("renders public issue cards and restores filters from the URL", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(trackerResponse())));

    renderTracker("/issues?category=streetlight&status=in_progress&sort=most_verified");

    expect(await screen.findByText("Broken streetlight near community park")).toBeInTheDocument();
    expect(screen.getByText("Live tracker")).toBeInTheDocument();
    expect(screen.getByText("Visible Signals")).toBeInTheDocument();
    expect(screen.getByText("Public signal")).toBeInTheDocument();
    expect(screen.getByText("Green Park · Community playground")).toBeInTheDocument();
    expect(screen.getByText("CP-20260625-00000001")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByLabelText("Category")).toHaveValue("streetlight");
    expect(screen.getByLabelText("Status")).toHaveValue("in_progress");
    expect(screen.getByLabelText("Sort by")).toHaveValue("most_verified");
    expect(screen.getByRole("tab", { name: "List" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("writes combined filters and search terms to the URL", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(trackerResponse())));
    renderTracker("/issues?page=3&category=streetlight");
    await screen.findByText("Broken streetlight near community park");

    await user.selectOptions(screen.getByLabelText("Severity"), "high");
    await user.selectOptions(screen.getByLabelText("Status"), "reported");
    await user.clear(screen.getByLabelText("Search by location"));
    await user.type(screen.getByLabelText("Search by location"), "Sector 12");
    await user.click(screen.getByRole("button", { name: "Search" }));

    const search = screen.getByTestId("current-search").textContent;
    expect(search).toContain("category=streetlight");
    expect(search).toContain("severity=high");
    expect(search).toContain("status=reported");
    expect(search).toContain("location=Sector+12");
    expect(search).not.toContain("page=3");
  });

  it("shows empty results and clears active filters", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(trackerResponse({ items: [], total_items: 0, total_pages: 0 })),
      ),
    );
    renderTracker("/issues?category=road_damage");

    expect(await screen.findByText("No issues match these filters")).toBeInTheDocument();
    const clearButtons = screen.getAllByRole("button", { name: "Clear filters" });
    await user.click(clearButtons[0]);

    expect(screen.getByTestId("current-search").textContent).toBe("");
  });

  it("moves between pages without losing filters", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(trackerResponse({ total_items: 24, total_pages: 2 })),
      ),
    );
    renderTracker("/issues?severity=critical");
    await screen.findByText("Broken streetlight near community park");

    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByTestId("current-search")).toHaveTextContent("severity=critical");
    expect(screen.getByTestId("current-search")).toHaveTextContent("page=2");
  });

  it("switches to URL-backed map view and loads marker data", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const path = routePath(input);
      if (path === "/api/v1/issues/map") {
        return Promise.resolve(jsonResponse(mapResponse()));
      }
      return Promise.resolve(jsonResponse(trackerResponse()));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderTracker("/issues?category=streetlight");

    await screen.findByText("Broken streetlight near community park");
    await user.click(screen.getByRole("tab", { name: "Map" }));

    expect(await screen.findByText("1 marker shown")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Map" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByTestId("current-search").textContent).toContain("view=map");
    expect(screen.getByTestId("current-search").textContent).toContain("category=streetlight");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/issues/map?category=streetlight"),
      expect.any(Object),
    );
  });

  it("shows empty map results and clears filters without leaving map view", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(mapResponse({ items: [], total_items: 0, unmapped_items: 0 })),
      ),
    );
    renderTracker("/issues?view=map&severity=critical");

    expect(await screen.findByText("No mappable issues match these filters")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Clear filters" })[0]);

    expect(screen.getByTestId("current-search").textContent).toBe("?view=map");
  });

  it("shows a recoverable API failure state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            error: {
              code: "request_failed",
              message: "Tracker temporarily unavailable.",
              details: [],
            },
          },
          503,
        ),
      ),
    );

    renderTracker("/issues");

    expect(
      await screen.findByText("The public tracker could not be loaded"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
