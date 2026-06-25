import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest } from "../src/api/client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiRequest", () => {
  it("parses successful JSON responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), {
          headers: { "Content-Type": "application/json" },
          status: 200,
        }),
      ),
    );

    await expect(apiRequest<{ ok: boolean }>("/test")).resolves.toEqual({ ok: true });
  });

  it("turns backend error envelopes into ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "validation_error",
              message: "Invalid report.",
              details: [{ field: "description" }],
              request_id: "request-123",
            },
          }),
          {
            headers: { "Content-Type": "application/json" },
            status: 422,
          },
        ),
      ),
    );

    const error = await apiRequest("/test").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      code: "validation_error",
      requestId: "request-123",
      status: 422,
    });
  });
});

