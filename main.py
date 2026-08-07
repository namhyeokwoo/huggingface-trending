#!/usr/bin/env python3
"""
┌─────────────────────────────────────────────────────────────────────────────┐
│  FILE ROLE  ·  main.py                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Entry point and pipeline orchestrator (허브 호출 진입점). CLI 플래그로 어떤│
│  스테이지를 실행할지 결정하고, 각 스테이지의 순수 함수를 직접 호출한다.      │
│  HF API를 직접 부르거나 HTML을 직접 그리지 않음 — 그건 세 스테이지 파일 몫. │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│  NAVIGATION                                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  main.py            ── ★ YOU ARE HERE  Entry point, orchestrates all stages │
│  fetch_snapshot.py  ── Stage 1: HF API → data/snapshots/YYYY-MM-DD.json     │
│  generate_report.py ── Stage 2: 스냅샷 비교 → report-*.html/latest/index    │
│  build_trends.py    ── Stage 3: 전체 스냅샷 → trends.html (Chart.js)        │
│  common.py           ── 경로 상수 + 스냅샷 로드/저장 + .env 로더             │
│  CLAUDE.md            ── Architecture overview, data-flow                    │
└─────────────────────────────────────────────────────────────────────────────┘
"""
import argparse
import webbrowser
from datetime import datetime, timedelta, timezone

import build_trends
import fetch_snapshot
import generate_report
from common import OUTPUT_DIR, list_snapshot_dates, load_snapshot, save_snapshot

KST = timezone(timedelta(hours=9))


def main():
    parser = argparse.ArgumentParser(description="Hugging Face Trending Report Generator")
    parser.add_argument("--cache", action="store_true",
                         help="HF API 재호출 없이 기존 스냅샷(가장 최근 날짜)으로 리포트만 재생성")
    parser.add_argument("--no-trends", action="store_true", help="추이 차트(Stage 3) 생략")
    parser.add_argument("--open", action="store_true", help="완료 후 latest.html을 기본 브라우저로 열기")
    args = parser.parse_args()

    print("\n" + "━" * 55)
    print("  🤗  Hugging Face Trending Report Generator")
    print("━" * 55)

    if args.cache:
        dates = list_snapshot_dates()
        if not dates:
            print("\n  ❌ No cached snapshots found — run without --cache first")
            raise SystemExit(1)
        date = dates[-1]
        print(f"\n📦 Using cached snapshot for {date} (--cache, no HF API call)")
    else:
        date = datetime.now(KST).strftime("%Y-%m-%d")
        print(f"\n📡 Fetching fresh snapshot for {date} …")
        models = fetch_snapshot.fetch_model_pool()
        save_snapshot(date, {
            "date": date,
            "fetched_at": datetime.now(KST).isoformat(),
            "source": "huggingface.co/api/models",
            "models": models,
        })
        print(f"  Models fetched   : {len(models)}")

    today = load_snapshot(date)
    prev_date = generate_report.find_previous_date(date)
    prev = load_snapshot(prev_date) if prev_date else None
    ranked, new_entrants = generate_report.compute_daily_ranking(today, prev)
    report_html = generate_report.render_html(date, prev_date, ranked, new_entrants)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / f"report-{date}.html").write_text(report_html, encoding="utf-8")
    (OUTPUT_DIR / "latest.html").write_text(report_html, encoding="utf-8")
    (OUTPUT_DIR / "index.html").write_text(generate_report.build_index_html(), encoding="utf-8")

    trending_count = 0
    if not args.no_trends:
        print("\n📈 Building trend chart …")
        series = build_trends.build_series()
        selected = build_trends.select_top_trending(series)
        trends_html = build_trends.render_html(build_trends.build_chart_data(series, selected))
        (OUTPUT_DIR / "trends.html").write_text(trends_html, encoding="utf-8")
        trending_count = len(selected)

    abs_path = (OUTPUT_DIR / "latest.html").resolve()
    print(f"\n✅ Report ready → {abs_path}")
    print(f"   Open manually : file://{abs_path}")

    if args.open:
        webbrowser.open(f"file://{abs_path}")
        print("   Browser launched 🚀")

    print("\n" + "━" * 55)
    print(f"  Models in snapshot : {len(today['models'])}")
    print(f"  New entrants       : {len(new_entrants)}")
    print(f"  Trending (chart)   : {trending_count}")
    print("  Report ready")
    print("━" * 55 + "\n")


if __name__ == "__main__":
    main()
