# === builder 階段：安裝相依 ===
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 編譯 asyncmy / bcrypt 等需要的工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# 下載 Swagger UI 靜態資源，供執行時本地提供（不依賴外部 CDN）
# 於 builder 階段下載一次；下載失敗不中斷 build（runtime 會 fallback 回 CDN）
RUN python - <<'PY'
import os, urllib.request
os.makedirs("/assets", exist_ok=True)
files = {
    "swagger-ui-bundle.js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
    "swagger-ui.css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
}
for name, url in files.items():
    try:
        urllib.request.urlretrieve(url, f"/assets/{name}")
        print("downloaded", name)
    except Exception as exc:
        print("WARN: failed to download", name, exc)
PY

# === runtime 階段：精簡映像 ===
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Taipei

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

COPY . .

# 將 builder 下載的 Swagger UI / ReDoc 靜態資源放入 app/static（本地提供，免 CDN）
COPY --from=builder /assets/ ./app/static/

EXPOSE 8000

# 進入點：secret 前置檢查 → Alembic 遷移 + 種子 → 啟動 uvicorn
# 安全檢查放在最前面，缺失/佔位 secret 時在任何 DB 操作前即 fail-fast（issue #1）
CMD ["sh", "-c", "python -m app.core.validate_startup && alembic upgrade head && python -m app.db.init_db && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
