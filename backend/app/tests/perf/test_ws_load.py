"""WebSocket 負載測試：模擬 ≥ 50 並發連線，驗證推送不中斷（對應 SC-002/SC-004）。

執行方式（需後端已啟動）：
    WS_BASE_URL=ws://localhost:8000 API_BASE_URL=http://localhost:8000 \
        python -m app.tests.perf.test_ws_load

本腳本非 pytest 測試，而是獨立負載工具。
"""
import os
import threading
import time

import httpx
from websocket import create_connection

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WS_BASE_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000")
CONNECTIONS = int(os.getenv("PERF_CONNECTIONS", "50"))

_results: list[int] = []
_lock = threading.Lock()


def _get_token() -> str:
    with httpx.Client(base_url=API_BASE_URL, timeout=10) as c:
        resp = c.post(
            "/api/auth/login",
            data={"username": os.getenv("PERF_USER", "user"), "password": os.getenv("PERF_PASS", "User@12345")},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


def _worker(token: str) -> None:
    received = 0
    try:
        ws = create_connection(f"{WS_BASE_URL}/ws/realtime?token={token}", timeout=10)
        end = time.time() + 5
        while time.time() < end:
            if ws.recv():
                received += 1
        ws.close()
    except Exception:
        pass
    with _lock:
        _results.append(received)


def run() -> None:
    token = _get_token()
    threads = [threading.Thread(target=_worker, args=(token,)) for _ in range(CONNECTIONS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ok = sum(1 for r in _results if r > 0)
    print(f"並發連線={CONNECTIONS} 成功收到推送的連線={ok} "
          f"總訊息={sum(_results)}")
    print("PASS" if ok >= CONNECTIONS * 0.9 else "FAIL（超過 10% 連線未收到推送）")


if __name__ == "__main__":
    run()
