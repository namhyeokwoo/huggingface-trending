"""공유 경로 상수 + 스냅샷 로드/저장 헬퍼 + .env 로더. 4개 스크립트가 공용으로 import."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).parent
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
OUTPUT_DIR = ROOT / "output"


def _load_dotenv():
    """.env의 KEY=VALUE 줄을 os.environ에 로드 (stdlib only, x-influencer-briefing/main.py와 동일 패턴)."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


_load_dotenv()


def snapshot_path(date: str) -> Path:
    return SNAPSHOT_DIR / f"{date}.json"


def save_snapshot(date: str, data: dict) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = snapshot_path(date)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_snapshot(date: str) -> dict | None:
    path = snapshot_path(date)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_snapshot_dates() -> list[str]:
    if not SNAPSHOT_DIR.exists():
        return []
    return sorted(p.stem for p in SNAPSHOT_DIR.glob("????-??-??.json"))


def load_all_snapshots() -> dict[str, dict]:
    return {date: load_snapshot(date) for date in list_snapshot_dates()}
