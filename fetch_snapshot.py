#!/usr/bin/env python3
"""
┌─────────────────────────────────────────────────────────────────────────────┐
│  FILE ROLE  ·  fetch_snapshot.py                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Stage 1. Hugging Face Hub 공개 API에서 좋아요순 + 다운로드순 상위 모델을    │
│  가져와 하나의 풀로 합친 뒤 data/snapshots/YYYY-MM-DD.json 으로 저장한다.    │
│  주의: HF API에는 sort=trending이 없다(400 에러, 직접 확인함) — "트렌딩"은  │
│  generate_report.py/build_trends.py가 스냅샷 간 증가폭으로 계산한다.        │
│  HF_TOKEN 환경변수가 있으면 Authorization 헤더에 실어 보내지만 선택 사항이며 │
│  없어도 공개 모델 조회는 인증 없이 정상 동작한다(하루 2회 호출, 500req/300s │
│  한도 대비 여유 충분).                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
"""
import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from common import save_snapshot

API_URL = "https://huggingface.co/api/models"
POOL_LIMIT = 300
KST = timezone(timedelta(hours=9))
FIELDS = ("id", "likes", "downloads", "pipeline_tag", "library_name", "createdAt", "lastModified")


def _fetch(sort: str, limit: int = POOL_LIMIT) -> list[dict]:
    url = f"{API_URL}?sort={sort}&direction=-1&limit={limit}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "huggingface-trending/1.0")
    token = os.environ.get("HF_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_model_pool(limit: int = POOL_LIMIT) -> list[dict]:
    """좋아요순 + 다운로드순 두 풀을 id 기준으로 합친다."""
    pool: dict[str, dict] = {}
    for sort in ("likes", "downloads"):
        for m in _fetch(sort, limit):
            model_id = m.get("id")
            if not model_id:
                continue
            pool[model_id] = {k: m.get(k) for k in FIELDS}
    return list(pool.values())


def main():
    parser = argparse.ArgumentParser(description="Fetch a Hugging Face trending-models snapshot")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (기본: 오늘, KST)")
    args = parser.parse_args()

    date = args.date or datetime.now(KST).strftime("%Y-%m-%d")

    print(f"\n📡 Fetching Hugging Face model pool (likes + downloads, limit={POOL_LIMIT} each) …")
    try:
        models = fetch_model_pool()
    except urllib.error.URLError as e:
        print(f"  ❌ Fetch failed: {e}")
        raise SystemExit(1)

    data = {
        "date": date,
        "fetched_at": datetime.now(KST).isoformat(),
        "source": "huggingface.co/api/models",
        "models": models,
    }
    path = save_snapshot(date, data)
    print(f"  Models fetched   : {len(models)}")
    print(f"  Snapshot saved   : {path}")


if __name__ == "__main__":
    main()
