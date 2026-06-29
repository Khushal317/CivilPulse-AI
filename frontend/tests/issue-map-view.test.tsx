import { act, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { IssueMapView } from "../src/features/issues/IssueMapView";
import type { PublicIssueMapResponse } from "../src/features/issues/types";
import { renderWithProviders } from "./test-utils";

const mapsMock = vi.hoisted(() => {
  class GoogleMapsConfigurationError extends Error {
    constructor() {
      super("Google Maps is not configured.");
      this.name = "GoogleMapsConfigurationError";
    }
  }

  return {
    GoogleMapsConfigurationError,
    boundsExtend: vi.fn(),
    infoWindowOpen: vi.fn(),
    infoWindowSetContent: vi.fn(),
    listenerRemove: vi.fn(),
    loadGoogleMaps: vi.fn(),
    mapFitBounds: vi.fn(),
    mapSetCenter: vi.fn(),
    mapSetZoom: vi.fn(),
    markerClickHandlers: [] as Array<() => void>,
    markerSetMap: vi.fn(),
  };
});

vi.mock("../src/lib/maps/googleMapsLoader", () => ({
  GoogleMapsConfigurationError: mapsMock.GoogleMapsConfigurationError,
  loadGoogleMaps: mapsMock.loadGoogleMaps,
}));

const mapResult: PublicIssueMapResponse = {
  items: [
    {
      id: "11111111-1111-4111-8111-111111111111",
      public_reference: "CP-20260625-00000001",
      title: "Broken streetlight near community park",
      category: "streetlight",
      severity: "high",
      status: "in_progress",
      location: "Green Park",
      landmark: "Community playground",
      neighborhood: "Green Park",
      latitude: 26.9124,
      longitude: 75.7873,
    },
  ],
  total_items: 1,
  unmapped_items: 2,
};

function fakeGoogleMaps() {
  return {
    maps: {
      InfoWindow: vi.fn().mockImplementation(() => ({
        close: vi.fn(),
        open: mapsMock.infoWindowOpen,
        setContent: mapsMock.infoWindowSetContent,
      })),
      LatLngBounds: vi.fn().mockImplementation(() => ({
        extend: mapsMock.boundsExtend,
      })),
      Map: vi.fn().mockImplementation(() => ({
        fitBounds: mapsMock.mapFitBounds,
        setCenter: mapsMock.mapSetCenter,
        setZoom: mapsMock.mapSetZoom,
      })),
      Marker: vi.fn().mockImplementation(() => ({
        addListener: vi.fn((_eventName: "click", callback: () => void) => {
          mapsMock.markerClickHandlers.push(callback);
          return { remove: mapsMock.listenerRemove };
        }),
        setMap: mapsMock.markerSetMap,
      })),
      places: {},
    },
  };
}

beforeEach(() => {
  mapsMock.boundsExtend.mockClear();
  mapsMock.infoWindowOpen.mockClear();
  mapsMock.infoWindowSetContent.mockClear();
  mapsMock.listenerRemove.mockClear();
  mapsMock.loadGoogleMaps.mockReset();
  mapsMock.mapFitBounds.mockClear();
  mapsMock.mapSetCenter.mockClear();
  mapsMock.mapSetZoom.mockClear();
  mapsMock.markerClickHandlers.length = 0;
  mapsMock.markerSetMap.mockClear();
});

describe("IssueMapView", () => {
  it("falls back to issue links when Google Maps is not configured", async () => {
    mapsMock.loadGoogleMaps.mockRejectedValue(new mapsMock.GoogleMapsConfigurationError());

    renderWithProviders(<IssueMapView result={mapResult} />, { route: "/issues?view=map" });

    expect(await screen.findByText("Map markers are ready")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Google Maps is not configured yet. Add a valid Maps JavaScript API key to show markers on the map.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("2 issues hidden from map because coordinates are not available yet."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Broken streetlight near community park" }),
    ).toHaveAttribute("href", "/issues/11111111-1111-4111-8111-111111111111");
  });

  it("creates markers and opens an issue detail popup", async () => {
    mapsMock.loadGoogleMaps.mockResolvedValue(fakeGoogleMaps());

    renderWithProviders(<IssueMapView result={mapResult} />, { route: "/issues?view=map" });

    expect(await screen.findByText("1 marker shown")).toBeInTheDocument();

    await waitFor(() => {
      expect(mapsMock.markerClickHandlers).toHaveLength(1);
    });

    expect(mapsMock.boundsExtend).toHaveBeenCalledWith({ lat: 26.9124, lng: 75.7873 });
    expect(mapsMock.mapSetCenter).toHaveBeenCalledWith({ lat: 26.9124, lng: 75.7873 });
    expect(mapsMock.mapSetZoom).toHaveBeenCalledWith(15);

    act(() => {
      mapsMock.markerClickHandlers[0]();
    });

    const popupHtml = mapsMock.infoWindowSetContent.mock.calls[0]?.[0] as string;
    expect(popupHtml).toContain("Broken streetlight near community park");
    expect(popupHtml).toContain("High");
    expect(popupHtml).toContain("In progress");
    expect(popupHtml).toContain("/issues/11111111-1111-4111-8111-111111111111");
    expect(mapsMock.infoWindowOpen).toHaveBeenCalledOnce();
  });
});
