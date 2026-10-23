"""容器啟動前置安全檢查入口（issue #1）。

於 Docker entrypoint 中「最先」執行，確保在 Alembic migration / init_db 等任何
DB 操作之前就完成 secret 驗證。缺失或佔位值時以非零離開碼終止，達成真正的
fail-fast（而非等到 DB 連線失敗）。

用法（Dockerfile CMD）：
    python -m app.core.validate_startup && alembic upgrade head && ...
"""
import sys

from app.core.config import validate_secrets


def main() -> int:
    try:
        validate_secrets()
    except RuntimeError as exc:
        # 寫到 stderr 並以非零碼離開，阻止後續 migration / 服務啟動
        print(str(exc), file=sys.stderr)
        return 1
    print("啟動前置安全檢查通過")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
