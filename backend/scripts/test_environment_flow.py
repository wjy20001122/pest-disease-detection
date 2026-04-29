from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import fastapi_app  # noqa: E402


def main() -> None:
    with TestClient(fastapi_app) as client:
        current_res = client.get(
            "/environment/current",
            params={"address": "测试田块"},
        )
        assert current_res.status_code == 200, current_res.text
        current = current_res.json()
        assert current["address"] == "测试田块"
        assert current["recorded_at"]

        manual_res = client.post(
            "/environment/manual",
            params={
                "address": "测试田块",
                "weather": "晴",
                "temperature": 26.5,
                "humidity": 61,
            },
        )
        assert manual_res.status_code == 200, manual_res.text
        manual = manual_res.json()
        assert manual["address"] == "测试田块"
        assert manual["weather"] == "晴"
        assert manual["temperature"] == 26.5
        assert manual["humidity"] == 61

    print("environment flow ok: current/manual fallback")


if __name__ == "__main__":
    main()
