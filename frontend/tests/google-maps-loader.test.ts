import { afterEach, describe, expect, it } from "vitest";

import {
  GoogleMapsConfigurationError,
  loadGoogleMaps,
  resetGoogleMapsLoaderForTests,
} from "../src/lib/maps/googleMapsLoader";

afterEach(() => {
  resetGoogleMapsLoaderForTests();
  delete window.google;
});

describe("googleMapsLoader", () => {
  it("rejects clearly when the API key is missing", async () => {
    await expect(loadGoogleMaps({ apiKey: "" })).rejects.toBeInstanceOf(
      GoogleMapsConfigurationError,
    );

    expect(document.querySelector("script[src*='maps.googleapis.com']")).not.toBeInTheDocument();
  });

  it("reuses an already available Google Maps global", async () => {
    const google = { maps: { places: {} } };
    window.google = google;

    await expect(loadGoogleMaps({ apiKey: "test-key" })).resolves.toBe(google);
  });

  it("loads Google Maps once with the Places library", async () => {
    const pendingLoad = loadGoogleMaps({ apiKey: "test-key" });
    const script = document.querySelector<HTMLScriptElement>(
      "script#civicpulse-google-maps-js",
    );

    expect(script).not.toBeNull();
    expect(script?.src).toContain("https://maps.googleapis.com/maps/api/js");
    expect(script?.src).toContain("key=test-key");
    expect(script?.src).toContain("libraries=places");

    const google = { maps: { places: {} } };
    window.google = google;
    window.__civicPulseGoogleMapsReady?.();

    await expect(pendingLoad).resolves.toBe(google);
  });
});
