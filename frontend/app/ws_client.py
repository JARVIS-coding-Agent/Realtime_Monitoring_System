"""WebSocket 客戶端：連線即時資料推送並讀取訊息。"""
import json
import os

from websocket import create_connection

WS_BASE_URL = os.getenv("WS_BASE_URL", "ws://backend:8000")


def fetch_realtime_batch(token: str, max_messages: int = 5, timeout: float = 3.0) -> list[dict]:
    """建立短連線，讀取數筆即時訊息後關閉（供 Streamlit 輪詢式更新）。"""
    messages: list[dict] = []
    ws = None
    try:
        ws = create_connection(f"{WS_BASE_URL}/ws/realtime?token={token}", timeout=timeout)
        for _ in range(max_messages):
            raw = ws.recv()
            if not raw:
                break
            try:
                messages.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
    return messages
