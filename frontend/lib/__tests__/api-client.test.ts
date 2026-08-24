import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, executeAction, getDataSummary, listOpportunities, planAction, runAIBatchAnalysis } from "../api-client";

function mockFetchOnce(body: unknown, ok = true, status = 200) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    statusText: ok ? "OK" : "Error",
    json: async () => body,
  }) as unknown as typeof fetch;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api-client", () => {
  it("getDataSummary calls the correct endpoint and returns parsed JSON", async () => {
    mockFetchOnce({ customers: 1200, subscriptions: 403, payments: 7348, payments_by_status: {}, recovery_cases: 1412 });

    const result = await getDataSummary();

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/data/summary"),
      expect.objectContaining({ headers: expect.any(Object) })
    );
    expect(result.customers).toBe(1200);
  });

  it("listOpportunities builds query params from filters", async () => {
    mockFetchOnce({ total: 0, limit: 25, offset: 0, opportunities: [] });

    await listOpportunities({ priority: "high", min_amount: 1000, limit: 10, offset: 20 });

    const calledUrl = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("priority=high");
    expect(calledUrl).toContain("min_amount=1000");
    expect(calledUrl).toContain("limit=10");
    expect(calledUrl).toContain("offset=20");
  });

  it("planAction POSTs to the per-case plan endpoint", async () => {
    mockFetchOnce({ already_planned: false, action: "retry_payment", reason: "ok", status: "planned" });

    await planAction("rec_test_1");

    const [url, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/api/recovery/opportunities/rec_test_1/plan");
    expect(init.method).toBe("POST");
  });

  it("executeAction POSTs to the per-case execute endpoint (never a bulk endpoint)", async () => {
    mockFetchOnce({
      already_executed: false,
      execution_status: "success",
      recovered_amount: 100,
      status: "recovered",
      failure_reason: null,
    });

    await executeAction("rec_test_2");

    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/api/recovery/opportunities/rec_test_2/execute");
    expect(url).not.toContain("bulk");
  });

  it("runAIBatchAnalysis defaults batch size to 10", async () => {
    mockFetchOnce({ batch_size: 10, cases_processed: 0, results: [] });

    await runAIBatchAnalysis();

    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("batch_size=10");
  });

  it("throws ApiError with the response detail on a non-ok response", async () => {
    mockFetchOnce({ detail: "Recovery opportunity not found" }, false, 404);

    await expect(planAction("rec_missing")).rejects.toBeInstanceOf(ApiError);
    await expect(planAction("rec_missing")).rejects.toThrow("Recovery opportunity not found");
  });
});
