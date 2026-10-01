# Twin — ZC 그림 인식

BTC 1시간 MACD 히스토그램의 파동 묶음(ZC0 → A극점 → ZC1 → L/H → ZC2)을 그림으로 보고,
진행 중인 그림이 어느 그룹 그림과 얼마나 비슷하고 맥락까지 맞는지 잰다. 미래 데이터는 쓰지 않는다.

- 원칙·설계·검증: `vault/` (옵시디언으로 열기) — `00_홈.md`부터
- 코드: `twin/` · 테스트: `tests/test_twin.py` · 지난 실험 장부: `archive/research_audit/`

## 사용
```bash
pip install -r requirements.txt
export TWIN_OHLCV=/path/to/bybit_btc_5m.parquet       # 5분봉 (저장소에 넣지 않음)

python -m twin.pipeline build  "$TWIN_OHLCV" shapes     # shapes/<그룹>/events/*.json + shapes/<그룹>/<그룹>.json
python -m twin.pipeline replay "$TWIN_OHLCV" result.csv # q-by-q 검증 (L/H +12봉)
python -m twin.pipeline now    "$TWIN_OHLCV"            # 지금 진행 중인 그림의 그룹 순위
python -m pytest -q tests/test_twin.py                  # 미래데이터 금지 테스트
```

## 에이전트 · 하네스 · MCP
- `.claude/agents/` — shape-builder(JSON 만들기) · lookahead-auditor(미래데이터 감사) · replay-validator(q-by-q 검증) · research-scribe(볼트 기록)
- `.claude/settings.json` — twin/ 수정 뒤 앞당기기 패턴 검사 + 테스트 자동 실행 (`.claude/hooks/after_edit.py`)
- `.mcp.json` → `twin/mcp_server.py` — build_tree · groups · event · find_now · replay · form_similarity · lookahead_check
