const defaultApiBaseUrl = "http://localhost:8000";
const configuredApiBaseUrl: unknown = import.meta.env.VITE_API_BASE_URL;
const apiBaseUrl =
  typeof configuredApiBaseUrl === "string" && configuredApiBaseUrl.length > 0
    ? configuredApiBaseUrl
    : defaultApiBaseUrl;

export const env = {
  apiBaseUrl: apiBaseUrl.replace(/\/$/, ""),
} as const;
