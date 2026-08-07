#!/usr/bin/env python3
"""
┌─────────────────────────────────────────────────────────────────────────────┐
│  FILE ROLE  ·  generate_report.py                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Stage 2. 오늘 스냅샷을 가장 최근 이전 스냅샷과 비교해 "어제 대비 좋아요     │
│  증가폭" 순으로 정렬한 일일 리포트를 만든다. 이전 스냅샷이 없으면(1일차)     │
│  좋아요 내림차순으로 폴백하고 안내 문구를 표시한다. output/report-{date}.html│
│  + output/latest.html(동일 내용) + output/index.html(과거 리포트 아카이브,  │
│  2초 지연 후 latest.html로 리다이렉트)을 생성한다.                          │
└─────────────────────────────────────────────────────────────────────────────┘
"""
import argparse
from datetime import datetime, timedelta, timezone

from common import OUTPUT_DIR, list_snapshot_dates, load_snapshot

KST = timezone(timedelta(hours=9))
TOP_N = 30
NEW_ENTRANT_N = 10


def find_previous_date(date: str) -> str | None:
    dates = [d for d in list_snapshot_dates() if d < date]
    return dates[-1] if dates else None


def compute_daily_ranking(today: dict, prev: dict | None) -> tuple[list[dict], list[dict]]:
    """(ranked, new_entrants) 튜플을 반환. prev가 None이면 new_entrants는 빈 리스트."""
    today_models = {m["id"]: m for m in today["models"]}

    if prev is None:
        ranked = sorted(today_models.values(), key=lambda m: m.get("likes") or 0, reverse=True)
        return ranked[:TOP_N], []

    prev_models = {m["id"]: m for m in prev["models"]}
    ranked, new_entrants = [], []
    for model_id, m in today_models.items():
        if model_id in prev_models:
            p = prev_models[model_id]
            entry = dict(m)
            entry["likes_delta"] = (m.get("likes") or 0) - (p.get("likes") or 0)
            entry["downloads_delta"] = (m.get("downloads") or 0) - (p.get("downloads") or 0)
            ranked.append(entry)
        else:
            new_entrants.append(dict(m))

    ranked.sort(key=lambda m: m.get("likes_delta", 0), reverse=True)
    new_entrants.sort(key=lambda m: m.get("likes") or 0, reverse=True)
    return ranked[:TOP_N], new_entrants[:NEW_ENTRANT_N]


def _fmt(n) -> str:
    return f"{n:,}" if isinstance(n, (int, float)) else "?"


def _fmt_delta(n: int) -> str:
    sign = "+" if n > 0 else ""
    return f"{sign}{n:,}"


def _row(m: dict, rank: int, show_delta: bool) -> str:
    delta_cell = ""
    if show_delta:
        d = m.get("likes_delta", 0)
        cls = "up" if d > 0 else ("down" if d < 0 else "flat")
        delta_cell = f'<td class="delta {cls}">{_fmt_delta(d)}</td>'
    url = f"https://huggingface.co/{m['id']}"
    return f"""
    <tr>
      <td class="rank">{rank}</td>
      <td class="model"><a href="{url}" target="_blank" rel="noopener">{m['id']}</a>
        <span class="tag">{m.get('pipeline_tag') or ''}</span></td>
      <td>{_fmt(m.get('likes'))}</td>
      <td>{_fmt(m.get('downloads'))}</td>
      {delta_cell}
    </tr>"""


def _entrant_row(m: dict, rank: int) -> str:
    url = f"https://huggingface.co/{m['id']}"
    return f"""
    <tr>
      <td class="rank">{rank}</td>
      <td class="model"><a href="{url}" target="_blank" rel="noopener">{m['id']}</a>
        <span class="tag">{m.get('pipeline_tag') or ''}</span></td>
      <td>{_fmt(m.get('likes'))}</td>
      <td>{_fmt(m.get('downloads'))}</td>
    </tr>"""


STYLE = """
  :root { --bg:#0f172a; --card:#1e293b; --text:#e2e8f0; --muted:#94a3b8;
          --accent:#f59e0b; --up:#34d399; --down:#f87171; --border:#334155; }
  * { box-sizing:border-box; }
  body { margin:0; padding:2rem 1rem 4rem; background:var(--bg); color:var(--text);
         font-family:-apple-system,"Segoe UI",Pretendard,sans-serif; }
  .wrap { max-width:960px; margin:0 auto; }
  h1 { font-size:1.5rem; margin:0 0 .25rem; }
  .sub { color:var(--muted); font-size:.9rem; margin:0 0 1.5rem; }
  nav.links { margin:0 0 1.5rem; display:flex; gap:1rem; }
  nav.links a { color:var(--accent); text-decoration:none; font-size:.9rem; }
  nav.links a:hover { text-decoration:underline; }
  .note { background:var(--card); border:1px solid var(--border); border-radius:8px;
          padding:.75rem 1rem; font-size:.85rem; color:var(--muted); margin-bottom:1.5rem; }
  table { width:100%; border-collapse:collapse; background:var(--card); border-radius:8px;
          overflow:hidden; margin-bottom:2rem; }
  th, td { padding:.6rem .8rem; text-align:right; border-bottom:1px solid var(--border);
           font-size:.9rem; }
  th:nth-child(2), td.model { text-align:left; }
  th { color:var(--muted); font-weight:600; font-size:.8rem; text-transform:uppercase; }
  td.rank { color:var(--muted); width:2.5rem; }
  td.model a { color:var(--text); text-decoration:none; font-weight:500; }
  td.model a:hover { text-decoration:underline; }
  .tag { display:block; color:var(--muted); font-size:.75rem; }
  .delta.up { color:var(--up); }
  .delta.down { color:var(--down); }
  .delta.flat { color:var(--muted); }
  h2 { font-size:1.1rem; margin:0 0 .75rem; }
"""


def render_html(date: str, prev_date: str | None, ranked: list[dict], new_entrants: list[dict]) -> str:
    show_delta = prev_date is not None
    rows = "".join(_row(m, i + 1, show_delta) for i, m in enumerate(ranked))
    delta_th = "<th>Δ 좋아요</th>" if show_delta else ""

    if prev_date:
        sub = f"{prev_date} 대비 좋아요 증가폭 기준 · {date} 09:00 KST 기준 수집"
        note = ""
    else:
        sub = f"{date} 09:00 KST 기준 수집 · 좋아요 내림차순"
        note = '<div class="note">ℹ️ 아직 이전 스냅샷이 없어 증가폭 대신 좋아요 순으로 표시합니다. 다음날부터 증가폭(Δ) 랭킹이 표시됩니다.</div>'

    entrants_section = ""
    if new_entrants:
        entrants_rows = "".join(_entrant_row(m, i + 1) for i, m in enumerate(new_entrants))
        entrants_section = f"""
    <h2>🆕 신규 진입 모델</h2>
    <table>
      <thead><tr><th></th><th>Model</th><th>Likes</th><th>Downloads</th></tr></thead>
      <tbody>{entrants_rows}</tbody>
    </table>"""

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>HF 트렌딩 모델 — {date}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{STYLE}</style></head>
<body><div class="wrap">
  <h1>🤗 Hugging Face 트렌딩 모델</h1>
  <p class="sub">{sub}</p>
  <nav class="links">
    <a href="trends.html">📈 모델 추이 보기</a>
    <a href="index.html">🗂 지난 리포트</a>
  </nav>
  {note}
  <table>
    <thead><tr><th></th><th>Model</th><th>Likes</th><th>Downloads</th>{delta_th}</tr></thead>
    <tbody>{rows}</tbody>
  </table>
  {entrants_section}
</div></body></html>"""


def build_index_html() -> str:
    dates = list(reversed(list_snapshot_dates()))
    report_dates = [d for d in dates if (OUTPUT_DIR / f"report-{d}.html").exists()]
    rows = "".join(
        f'<tr><td>{d}</td><td><a href="report-{d}.html">리포트 보기</a></td></tr>'
        for d in report_dates
    )
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>HF 트렌딩 — 지난 리포트</title>
<meta http-equiv="refresh" content="2; url=latest.html">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{STYLE}</style></head>
<body><div class="wrap">
  <h1>🤗 HF 트렌딩 — 지난 리포트</h1>
  <p class="sub">2초 후 <a href="latest.html">최신 리포트</a>로 자동 이동합니다.</p>
  <table>
    <thead><tr><th>날짜</th><th></th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div></body></html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate the daily HF trending report")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (기본: 오늘, KST)")
    args = parser.parse_args()

    date = args.date or datetime.now(KST).strftime("%Y-%m-%d")
    today = load_snapshot(date)
    if today is None:
        print(f"  ❌ Snapshot not found for {date} — run fetch_snapshot.py first")
        raise SystemExit(1)

    prev_date = find_previous_date(date)
    prev = load_snapshot(prev_date) if prev_date else None

    ranked, new_entrants = compute_daily_ranking(today, prev)
    html = render_html(date, prev_date, ranked, new_entrants)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / f"report-{date}.html").write_text(html, encoding="utf-8")
    (OUTPUT_DIR / "latest.html").write_text(html, encoding="utf-8")
    (OUTPUT_DIR / "index.html").write_text(build_index_html(), encoding="utf-8")

    print(f"  Models in snapshot : {len(today['models'])}")
    print(f"  Ranked (top)       : {len(ranked)}")
    print(f"  New entrants       : {len(new_entrants)}")
    print("  Report ready")


if __name__ == "__main__":
    main()
