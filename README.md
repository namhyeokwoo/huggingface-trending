# HF 트렌딩 모델 리포트

Hugging Face Hub의 트렌딩 모델을 매일 추적해 좋아요/다운로드 증가폭 기준 일일
리포트와 시계열 추이 차트를 만드는 자동화 도구.

## 빠른 시작

```bash
python fetch_snapshot.py      # 오늘자 스냅샷 수집 → data/snapshots/YYYY-MM-DD.json
python generate_report.py     # output/report-*.html + latest.html + index.html
python build_trends.py        # output/trends.html (최소 2일치 스냅샷 필요)

# 또는 한 번에:
python main.py                # 전체 파이프라인 (fetch → report → trends)
python main.py --cache        # HF API 재호출 없이 기존 스냅샷으로 리포트만 재생성
python main.py --open         # 완료 후 latest.html을 브라우저로 열기
```

## 핵심 흐름

1. `fetch_snapshot.py` — `huggingface.co/api/models`를 좋아요순/다운로드순으로 각 300개씩
   조회해 합친 뒤 `data/snapshots/YYYY-MM-DD.json`에 저장 (인증 불필요, 하루 2회 호출)
2. `generate_report.py` — 오늘 스냅샷과 가장 최근 이전 스냅샷을 비교해 좋아요 증가폭 순
   리포트 생성. 이전 스냅샷이 없으면(1일차) 좋아요 내림차순으로 폴백
3. `build_trends.py` — 누적된 모든 스냅샷에서 상위 트렌딩 모델 15개의 좋아요 추이를
   Chart.js 라인차트로 렌더링
4. GitHub Actions가 매일 09:00 KST에 위 파이프라인을 실행하고 `data/`+`output/`을 커밋,
   GitHub Pages가 `output/`을 자동 배포

자세한 아키텍처는 [CLAUDE.md](CLAUDE.md) 참고.

## 환경 변수 (선택)

`HF_TOKEN` — 없어도 정상 동작(공개 API, 하루 2회 호출로 레이트리밋 여유 충분). 추가 여유가
필요하면 `.env.example`을 `.env`로 복사해 값 채우기.
