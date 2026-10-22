"""REST 讀取端點壓測：量測 GET /api/data P95 延遲（對應 SC-003 ≤ 300 ms）。

執行方式（需後端已啟動並可連線）：
    API_BASE_URL=http://localhost:8000 python -m app.tests.perf.test_rest_latency

本腳本非 pytest 測試，而是獨立壓測工具，避免在單元測試中依賴運行中的服務。
"""
import os
import statistics
import time

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REQUESTS = int(os.getenv("PERF_REQUESTS", "200"))
P95_TARGET_MS = 300.0


def run() -> None:
    with httpx.Client(base_url=API_BASE_URL, timeout=10) as c:
        login = c.post(
            "/api/auth/login",
            data={"username": os.getenv("PERF_USER", "user"), "password": os.getenv("PERF_PASS", "User@12345")},
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        latencies: list[float] = []
        for _ in range(REQUESTS):
            start = time.perf_counter()
            resp = c.get("/api/data", params={"page": 1, "page_size": 20}, headers=headers)
            resp.raise_for_status()
            latencies.append((time.perf_counter() - start) * 1000)

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    print(f"請求數={REQUESTS} 平均={statistics.mean(latencies):.1f}ms "
          f"P50={statistics.median(latencies):.1f}ms P95={p95:.1f}ms")
    print("PASS" if p95 <= P95_TARGET_MS else f"FAIL（P95 超過目標 {P95_TARGET_MS}ms）")


if __name__ == "__main__":
    run()
