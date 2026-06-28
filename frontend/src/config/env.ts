const defaultApiBaseUrl = "http://localhost:8000";
const configuredApiBaseUrl: unknown = import.meta.env.VITE_API_BASE_URL;
const configuredGoogleMapsApiKey: unknown = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

const apiBaseUrl =
  typeof configuredApiBaseUrl === "string" && configuredApiBaseUrl.length > 0
    ? configuredApiBaseUrl
    : defaultApiBaseUrl;
const googleMapsApiKey =
  typeof configuredGoogleMapsApiKey === "string" ? configuredGoogleMapsApiKey.trim() : "";

export const env = {
  apiBaseUrl: apiBaseUrl.replace(/\/$/, ""),
  googleMapsApiKey,
  isGoogleMapsConfigured: googleMapsApiKey.length > 0,
} as const;
