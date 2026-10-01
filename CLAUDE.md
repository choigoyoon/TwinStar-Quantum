# Twin — ZC 그림 인식 (v2)

1시간 MACD(12,26,9) 히스토그램의 한 파동 묶음(ZC0 → A극점 → ZC1 → B극점(L/H) → ZC2)을 **그림**으로 보고,
진행 중인 그림이 어느 그룹 그림과 **얼마나 비슷하고 맥락까지 맞는지(SIMILARITY / CONTEXT FIT)** 를 잰다.
기준 문서: `vault/02_그림JSON_설계서.md`. 이 문서와 다른 인식 방식은 runtime에 두지 않는다.

## 절대 규칙 — 미래 데이터 금지
- 봉의 시각 = 봉 시작. i번째 봉 종가로 만든 값은 그 봉이 끝난 뒤(시각 + 봉 길이)부터만 쓸 수 있다.
- runtime(현재 그림)이 쓰는 값: q 직전 5분봉까지의 관측 + ZC1 마감 때 이미 아는 기준값뿐.
- runtime 금지: 최종 L/H, 최종 사건 길이, ZC2, 사건 끝, 소속 그룹(답지). 답지는 JSON의 `answer` 칸과 평가 코드에서만.
- 큰 봉(15m·1h·4h) 값은 **마감된 봉만**. `shift(-k)`, `iloc[i+1:]` 같은 앞당기기 금지.
- 검증은 자기 사건을 뺀 기억(LOEO)으로. 더 엄격한 판은 그 시각 뒤에 끝난 사건도 뺀다. 사건 ID별 예외 금지.
- 새 계산을 넣으면 `tests/test_twin.py`에 "q 뒤 값을 바꿔도 결과가 같다" 테스트를 같이 넣는다.

## 구조
- `twin/data.py` 5분봉 읽기·리샘플 · `twin/zc.py` ZC 구간 · `twin/groups.py` 27칸 그룹 규칙
- `twin/shape.py` 사건 JSON(6채널) · 현재 그림 · 그룹 기억 · 점수
- `twin/pipeline.py` build / replay / now · `twin/mcp_server.py` 에이전트용 MCP 도구 (`.mcp.json`)
- `vault/` 옵시디언 노트 (원칙·설계·검증·실험 기록) · `archive/research_audit/` 지난 실험 장부(보존, 수정 금지)
- 에이전트: `.claude/agents/` — shape-builder, lookahead-auditor, replay-validator, research-scribe

## 작업 규칙
- 테스트: `python -m pytest -q tests/test_twin.py` (twin/ 수정 뒤 훅이 자동 실행)
- 데이터(parquet·원본 CSV)는 저장소에 넣지 않는다. 경로는 `TWIN_OHLCV` 환경변수.
- 결과 보고는 숫자를 숨기지 않는다: 실패 사건 주소와 이유, 동시에 "맞다"고 나온 그룹 수까지.
- 실험이 끝나면 `vault/04_실험기록/`에 날짜별 노트를 남긴다.
