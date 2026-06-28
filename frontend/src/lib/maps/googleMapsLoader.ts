import { env } from "../../config/env";

const GOOGLE_MAPS_SCRIPT_ID = "civicpulse-google-maps-js";
const GOOGLE_MAPS_CALLBACK_NAME = "__civicPulseGoogleMapsReady";
const DEFAULT_LIBRARIES: GoogleMapsLibrary[] = ["places"];

type GoogleMapsLibrary = "places";

export type GoogleMapsLoadStatus = "idle" | "loading" | "not_configured" | "ready";

export interface GoogleMapsGlobal {
  maps: {
    Map?: unknown;
    places?: unknown;
  };
}

declare global {
  interface Window {
    google?: GoogleMapsGlobal;
    __civicPulseGoogleMapsReady?: () => void;
  }
}

export interface LoadGoogleMapsOptions {
  apiKey?: string;
  libraries?: GoogleMapsLibrary[];
}

export class GoogleMapsConfigurationError extends Error {
  constructor() {
    super(
      "Google Maps is not configured. Add VITE_GOOGLE_MAPS_API_KEY to the frontend environment.",
    );
    this.name = "GoogleMapsConfigurationError";
  }
}

let loadPromise: Promise<GoogleMapsGlobal> | null = null;

const getMapsWindow = (): Window => window;

export const getGoogleMapsLoadStatus = (): GoogleMapsLoadStatus => {
  const mapsWindow = getMapsWindow();

  if (mapsWindow.google?.maps) {
    return "ready";
  }

  if (loadPromise) {
    return "loading";
  }

  return env.isGoogleMapsConfigured ? "idle" : "not_configured";
};

export const loadGoogleMaps = ({
  apiKey = env.googleMapsApiKey,
  libraries = DEFAULT_LIBRARIES,
}: LoadGoogleMapsOptions = {}): Promise<GoogleMapsGlobal> => {
  const normalizedApiKey = apiKey.trim();
  const mapsWindow = getMapsWindow();

  if (mapsWindow.google?.maps) {
    return Promise.resolve(mapsWindow.google);
  }

  if (!normalizedApiKey) {
    return Promise.reject(new GoogleMapsConfigurationError());
  }

  if (loadPromise) {
    return loadPromise;
  }

  loadPromise = new Promise<GoogleMapsGlobal>((resolve, reject) => {
    mapsWindow[GOOGLE_MAPS_CALLBACK_NAME] = () => {
      if (mapsWindow.google?.maps) {
        resolve(mapsWindow.google);
        return;
      }

      loadPromise = null;
      reject(new Error("Google Maps loaded, but the Maps API was unavailable."));
    };

    const script = document.createElement("script");
    const params = new URLSearchParams({
      callback: GOOGLE_MAPS_CALLBACK_NAME,
      key: normalizedApiKey,
      libraries: libraries.join(","),
      loading: "async",
    });

    script.id = GOOGLE_MAPS_SCRIPT_ID;
    script.async = true;
    script.defer = true;
    script.src = `https://maps.googleapis.com/maps/api/js?${params.toString()}`;
    script.onerror = () => {
      loadPromise = null;
      delete mapsWindow[GOOGLE_MAPS_CALLBACK_NAME];
      reject(new Error("Google Maps could not be loaded. Check the API key and network access."));
    };

    document.head.appendChild(script);
  });

  return loadPromise;
};

export const resetGoogleMapsLoaderForTests = (): void => {
  loadPromise = null;

  const mapsWindow = getMapsWindow();
  delete mapsWindow[GOOGLE_MAPS_CALLBACK_NAME];

  document.getElementById(GOOGLE_MAPS_SCRIPT_ID)?.remove();
};
