import { afterEach, describe, expect, it, vi } from "vitest";

import { analyzeReport } from "../src/features/reports/api";
import type { ReportFormValues } from "../src/features/reports/types";

afterEach(() => {
  vi.unstubAllGlobals();
});

function fileListWith(file: File): FileList {
  return {
    0: file,
    [Symbol.iterator]: function* iterateFiles() {
      yield file;
    },
    item: (index: number) => (index === 0 ? file : null),
    length: 1,
  } as unknown as FileList;
}

function reportValues(overrides: Partial<ReportFormValues> = {}): ReportFormValues {
  return {
    citizenContact: "",
    citizenName: "",
    image: fileListWith(new File(["image"], "issue.png", { type: "image/png" })),
    landmark: "",
    latitude: null,
    location: "Sector 12",
    longitude: null,
    originalDescription: "There is a large pothole near the school gate.",
    preferredCategory: "",
    urgencyNote: "",
    ...overrides,
  };
}

describe("analyzeReport", () => {
  it("sends coordinates when a Google place was selected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
        const body = init?.body as FormData;

        expect(body.get("location")).toBe("City Public School, Sector 12");
        expect(body.get("latitude")).toBe("26.9124");
        expect(body.get("longitude")).toBe("75.7873");

        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "11111111-1111-4111-8111-111111111111",
            }),
            {
              headers: { "Content-Type": "application/json" },
              status: 201,
            },
          ),
        );
      }),
    );

    await analyzeReport(
      reportValues({
        latitude: 26.9124,
        location: "City Public School, Sector 12",
        longitude: 75.7873,
      }),
    );
  });

  it("omits coordinates for manual text-only locations", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
        const body = init?.body as FormData;

        expect(body.get("location")).toBe("Sector 12");
        expect(body.has("latitude")).toBe(false);
        expect(body.has("longitude")).toBe(false);

        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "11111111-1111-4111-8111-111111111111",
            }),
            {
              headers: { "Content-Type": "application/json" },
              status: 201,
            },
          ),
        );
      }),
    );

    await analyzeReport(reportValues());
  });
});
