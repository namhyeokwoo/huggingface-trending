# HF 트렌딩 모델 리포트 — Architecture Overview

Hugging Face Hub의 트렌딩 모델을 매일 추적하는 자동화 도구. HF 공개 API에는
`sort=trending`이 없어서(400 에러, 직접 확인함) "트렌딩"은 우리가 매일 쌓는
스냅샷 간 좋아요/다운로드 증가폭으로 직접 계산한다. `x-influencer-briefing`,
`AI Weekly Paper Briefing`과 동일한 fetch → process → render 다단 파이프라인
컨벤션을 따르되, 이 프로젝트는 LLM 호출이 없다(순수 API 수집 + 집계 + 렌더링).

---

## File Map

| File                | Role                                        | Key Symbols                                              |
|---------------------|----------------------------------------------|------------------------------------------------------------|
| main.py             | Entry point, pipeline orchestrator          | `main()`                                                    |
| fetch_snapshot.py   | Stage 1: HF API → 스냅샷 저장               | `fetch_model_pool()`, `_fetch()`                            |
| generate_report.py  | Stage 2: 스냅샷 비교 → 일일 리포트          | `compute_daily_ranking()`, `render_html()`, `build_index_html()` |
| build_trends.py     | Stage 3: 전체 스냅샷 → 추이 차트            | `build_series()`, `select_top_trending()`, `render_html()` |
| common.py           | 경로 상수 + 스냅샷 로드/저장 + .env 로더    | `save_snapshot()`, `load_snapshot()`, `load_all_snapshots()` |
| CLAUDE.md           | This file — architecture reference          |                                                              |

---

## Data Flow

```
main.py
  │
  ├─[--cache]─── data/snapshots/{최신 날짜}.json (재사용, HF API 호출 없음)
  │
  └─[default]─── fetch_snapshot.fetch_model_pool()
                    │  huggingface.co/api/models?sort=likes  (top 300)
                    │  huggingface.co/api/models?sort=downloads (top 300)
                    │  id 기준 union
                    ▼
              data/snapshots/YYYY-MM-DD.json
                    │
                    ▼
              generate_report.compute_daily_ranking(today, prev)
                    │  prev 있음 → 좋아요 증가폭(delta) 순
                    │  prev 없음(1일차) → 좋아요 내림차순 폴백
                    ▼
       output/report-{date}.html + latest.html + index.html
                    │
          [--no-trends? skip]
                    ▼
              build_trends.select_top_trending()
                    │  2회 이상 등장 모델 중 (최신 좋아요 - 최초 등장 시 좋아요) 상위 15
                    ▼
              output/trends.html (Chart.js, CDN 로드)
```

## Snapshot Schema (`data/snapshots/YYYY-MM-DD.json`)

```json
{
  "date": "2026-08-07",
  "fetched_at": "2026-08-07T09:00:12+09:00",
  "source": "huggingface.co/api/models",
  "models": [
    {"id": "org/model-name", "likes": 1234, "downloads": 56789,
     "pipeline_tag": "text-generation", "library_name": "transformers",
     "createdAt": "...", "lastModified": "..."}
  ]
}
```

## "트렌딩" 정의 2종 (의도적으로 분리)

| 용도               | 함수                                        | 기준                                              |
|--------------------|-----------------------------------------------|-----------------------------------------------------|
| 일일 다이제스트   | `generate_report.compute_daily_ranking()`     | 어제 대비 오늘 좋아요 증가폭 (하루 단위)             |
| 시계열 차트       | `build_trends.select_top_trending()`          | 추적 기간 내 최초 등장 대비 최신 좋아요 증가폭 (누적) |

하나로 억지로 합치지 않음 — 일일 랭킹과 누적 추이는 답이 다를 수 있는 별개 질문.

## Environment

- **Python**: 3.10+ (`list[dict]` 등 타입힌트 사용)
- **Dependencies**: stdlib only — `urllib`, `json`, `datetime`, `argparse`, `pathlib`, `webbrowser`
- **HF_TOKEN** (선택): 없어도 정상 동작. `.env.example` 참고.

## CLI Reference

```
python main.py [flags]
  (no flags)     Full pipeline: HF API fetch → report → trends
  --cache        HF API 재호출 없이 가장 최근 스냅샷으로 리포트/추이만 재생성
  --no-trends    Stage 3(추이 차트) 생략
  --open         완료 후 latest.html을 기본 브라우저로 열기
```

## GitHub Actions

- `daily_report.yml` — 매일 00:00 UTC(09:00 KST) `python main.py` 실행 후 `data/snapshots`
  + `output`을 커밋·푸시. 커밋/푸시는 하나의 `if ! git diff --cached --quiet; then ... fi`
  블록 안에서 처리 — `zdnet-event-app`에서 겪은 버그(커밋 직후 두번째 diff 체크가 항상
  clean이라 push가 영원히 스킵됨)를 반복하지 않기 위함
- `pages.yml` — `output/**` 변경 시 `actions/deploy-pages`로 GitHub Pages 배포
  (`zdnet-event-app`/`hub-app`과 동일한 배포 메커니즘)

## Common Edit Tasks

| I want to…                          | Edit this                                          |
|--------------------------------------|-----------------------------------------------------|
| 풀 크기(300개) 변경                  | `POOL_LIMIT` in fetch_snapshot.py                  |
| 일일 리포트 상위 노출 개수 변경      | `TOP_N` in generate_report.py                      |
| 추이 차트 모델 개수 변경             | `TOP_N` in build_trends.py                          |
| 리포트 색상/스타일 변경              | `STYLE` in generate_report.py                       |
| 아카이브 리다이렉트 지연시간 변경    | `content="2;` in `build_index_html()`               |
| CLI 플래그 추가                      | `argparse` 블록 in main.py                          |
