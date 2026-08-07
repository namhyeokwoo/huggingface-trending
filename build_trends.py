#!/usr/bin/env python3
"""
┌─────────────────────────────────────────────────────────────────────────────┐
│  FILE ROLE  ·  build_trends.py                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Stage 3. data/snapshots/ 전체를 모아 모델별 좋아요 시계열을 만들고, 2회 이상│
│  등장한 모델 중 "최초 등장 대비 최신 좋아요 증가폭" 상위 15개를 Chart.js    │
│  라인차트(output/trends.html)로 그린다. generate_report.py의 "하루 전 대비  │
│  증가폭" 랭킹과는 다른 시계열 전용 기준이라 의도적으로 별도 함수로 분리함.   │
│  Chart.js는 CDN에서 로드한다 — 이 워크스페이스에서 유일한 외부 CDN 의존     │
│  예외이며, GitHub Pages로 온라인에서만 열람되는 파일이라 허용.               │
└─────────────────────────────────────────────────────────────────────────────┘
"""
import argparse
import json

from common import OUTPUT_DIR, load_all_snapshots

TOP_N = 15
PALETTE = [
    "#f59e0b", "#34d399", "#60a5fa", "#f87171", "#a78bfa",
    "#fb923c", "#4ade80", "#38bdf8", "#f472b6", "#facc15",
    "#2dd4bf", "#c084fc", "#fbbf24", "#818cf8", "#e879f9",
]


def build_series() -> dict[str, list[dict]]:
    """{model_id: [{date, likes, downloads}, ...]} 시간순."""
    snapshots = load_all_snapshots()
    series: dict[str, list[dict]] = {}
    for date in sorted(snapshots.keys()):
        for m in snapshots[date]["models"]:
            series.setdefault(m["id"], []).append({
                "date": date,
                "likes": m.get("likes") or 0,
                "downloads": m.get("downloads") or 0,
            })
    return series


def select_top_trending(series: dict[str, list[dict]], top_n: int = TOP_N) -> list[str]:
    """2회 이상 등장한 모델 중 최초 등장 대비 최신 좋아요 증가폭 상위 top_n."""
    scored = []
    for model_id, points in series.items():
        if len(points) < 2:
            continue
        growth = points[-1]["likes"] - points[0]["likes"]
        scored.append((growth, model_id))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [model_id for _, model_id in scored[:top_n]]


def build_chart_data(series: dict[str, list[dict]], selected: list[str]) -> dict:
    all_dates = sorted({p["date"] for mid in selected for p in series[mid]})
    datasets = []
    for i, model_id in enumerate(selected):
        by_date = {p["date"]: p["likes"] for p in series[model_id]}
        datasets.append({
            "label": model_id,
            "data": [by_date.get(d) for d in all_dates],
            "borderColor": PALETTE[i % len(PALETTE)],
            "backgroundColor": PALETTE[i % len(PALETTE)],
            "spanGaps": True,
            "tension": 0.25,
            "pointRadius": 2,
        })
    return {"labels": all_dates, "datasets": datasets}


def render_html(chart_data: dict) -> str:
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>HF 트렌딩 — 모델 추이</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root {{ --bg:#0f172a; --card:#1e293b; --text:#e2e8f0; --muted:#94a3b8; --accent:#f59e0b; }}
  body {{ margin:0; padding:2rem 1rem 4rem; background:var(--bg); color:var(--text);
          font-family:-apple-system,"Segoe UI",Pretendard,sans-serif; }}
  .wrap {{ max-width:1000px; margin:0 auto; }}
  h1 {{ font-size:1.5rem; margin:0 0 .25rem; }}
  .sub {{ color:var(--muted); font-size:.9rem; margin:0 0 1rem; }}
  nav.links {{ margin:0 0 1.5rem; }}
  nav.links a {{ color:var(--accent); text-decoration:none; font-size:.9rem; }}
  nav.links a:hover {{ text-decoration:underline; }}
  .chart-box {{ background:var(--card); border-radius:8px; padding:1rem; }}
  .empty {{ color:var(--muted); padding:2rem 0; text-align:center; }}
</style></head>
<body><div class="wrap">
  <h1>📈 Hugging Face 모델 추이</h1>
  <p class="sub">스냅샷 최소 2일치가 쌓인 모델 중 좋아요 증가폭 상위 {TOP_N}개 · 범례 클릭으로 라인 토글</p>
  <nav class="links"><a href="latest.html">← 오늘의 리포트</a></nav>
  <div class="chart-box">
    {'<canvas id="chart" height="110"></canvas>' if chart_data['datasets'] else '<p class="empty">아직 추이를 그릴 만큼 스냅샷이 쌓이지 않았습니다 (최소 2일 필요).</p>'}
  </div>
</div>
<script>
  const TREND_DATA = {json.dumps(chart_data, ensure_ascii=False)};
  if (TREND_DATA.datasets.length) {{
    new Chart(document.getElementById('chart'), {{
      type: 'line',
      data: TREND_DATA,
      options: {{
        responsive: true,
        interaction: {{ mode: 'nearest', intersect: false }},
        plugins: {{ legend: {{ labels: {{ color: '#e2e8f0' }} }} }},
        scales: {{
          x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }},
          y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }}
        }}
      }}
    }});
  }}
</script>
</body></html>"""


def main():
    parser = argparse.ArgumentParser(description="Build the HF trending time-series chart")
    parser.parse_args()

    series = build_series()
    selected = select_top_trending(series)
    chart_data = build_chart_data(series, selected)
    html = render_html(chart_data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "trends.html").write_text(html, encoding="utf-8")

    print(f"  Snapshots used   : {len(load_all_snapshots())}")
    print(f"  Trending models  : {len(selected)}")
    print("  Trends ready")


if __name__ == "__main__":
    main()
