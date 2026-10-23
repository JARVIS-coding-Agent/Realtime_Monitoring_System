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

EXPOSE 8000

# 進入點：secret 前置檢查 → Alembic 遷移 + 種子 → 啟動 uvicorn
# 安全檢查放在最前面，缺失/佔位 secret 時在任何 DB 操作前即 fail-fast（issue #1）
CMD ["sh", "-c", "python -m app.core.validate_startup && alembic upgrade head && python -m app.db.init_db && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
