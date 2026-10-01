"""
에이전트용 MCP 서버 — 프로젝트 기능을 AI 에이전트가 도구로 직접 부름

실행:  TWIN_OHLCV=<5분봉.parquet> python -m twin.mcp_server          (stdio)
Claude Code 등록: .mcp.json 의 "twin" 항목

도구
  build_tree(out_dir)              5분봉 → 사건 JSON + 그룹 JSON 폴더
  groups()                         그룹 목록과 사건 수, self_fit 요약
  event(event_id)                  사건 하나의 JSON
  find_now(as_of)                  as_of 시각(없으면 마지막)까지의 진행 중 그림 → 그룹 순위와 채널 점수
  replay(event_id)                 사건 하나를 q-by-q (자기 빼고), L/H +12봉 판정
  form_similarity(event_id)        1단계: 사건 JSON → 다시 그림 → 원 차트와 비교
  lookahead_check()                미래데이터 금지 테스트 실행
"""

import json
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
from mcp.server.fastmcp import FastMCP

from twin import pipeline as pl
from twin.shape import event_json, state

ROOT = Path(__file__).resolve().parents[1]
mcp = FastMCP('twin')


@lru_cache(maxsize=1)
def _df5() -> pd.DataFrame:
    path = os.environ.get('TWIN_OHLCV')
    if not path:
        raise RuntimeError('TWIN_OHLCV 환경변수에 5분봉 parquet 경로를 넣어 주세요')
    return pl.load(path)


@lru_cache(maxsize=4)
def _lib(as_of: Optional[str] = None) -> pl.Library:
    df5 = _df5()
    if as_of:
        df5 = df5[df5.index < pd.Timestamp(as_of)]
    return pl.Library(df5)


@mcp.tool()
def build_tree(out_dir: str = 'shapes') -> str:
    """5분봉에서 사건 JSON(<그룹>/events/*.json)과 그룹 JSON(<그룹>/<그룹>.json)을 만든다. 그룹별 사건 수를 돌려준다."""
    return json.dumps(_lib().export(str(ROOT / out_dir)), ensure_ascii=False)


@mcp.tool()
def groups() -> str:
    """그룹 목록, 사건 수, 채널별 self_fit 중앙값."""
    lib = _lib()
    out = {}
    for g in sorted(set(lib.groups)):
        sf = lib.mem.self_fit[g]
        out[g] = {'n': lib.groups.count(g), 'self_fit_p50': {c: round(float(pd.Series(v).median()), 4) for c, v in sf.items()}}
    return json.dumps(out, ensure_ascii=False)


@mcp.tool()
def event(event_id: str) -> str:
    """사건 하나의 JSON (event_id = ZC2 시각 'YYYY-MM-DDTHH')."""
    lib = _lib()
    i = lib.by_id[event_id]
    e = lib.events[i]
    return json.dumps(event_json(e, lib.full[i], e['grp'], e['eid']), ensure_ascii=False, default=pl._js_default)


@mcp.tool()
def find_now(as_of: Optional[str] = None, top: int = 5) -> str:
    """as_of 시각 직전까지(없으면 데이터 끝까지) 관측으로 진행 중 그림을 만들어 그룹 순위와 채널 점수를 돌려준다."""
    lib = _lib(as_of)
    ev = pl.live_event(lib.df5)
    st = state(ev, ev['N']) if ev else None
    if st is None:
        return json.dumps({'status': 'ZC1 마감 전 — 비교할 그림 없음'}, ensure_ascii=False)
    R = lib.rank(st).head(top).round(4)
    return json.dumps({'zc0': str(ev['zc0']), 'zc1': str(ev['zc1']), 'side': 'L' if ev['d'] > 0 else 'H',
                       'ranking': R.to_dict('records')}, ensure_ascii=False)


@mcp.tool()
def replay(event_id: str, step: int = 6) -> str:
    """사건 하나를 ZC1 마감부터 q-by-q로 다시 흘린 기록 (자기 자신은 기억에서 뺌). deadline=True 행이 L/H+12봉."""
    lib = _lib()
    return lib.replay(lib.by_id[event_id], step).round(4).to_json(orient='records', force_ascii=False)


@mcp.tool()
def form_similarity(event_id: str) -> str:
    """사건 JSON을 다시 그려 원 차트와 비교 (모양 상관, 뼈대 순서 일치, 평균 오차)."""
    lib = _lib()
    return json.dumps(lib.form_similarity(lib.by_id[event_id]), ensure_ascii=False)


@mcp.tool()
def lookahead_check() -> str:
    """미래데이터 금지 테스트(tests/test_twin.py)를 돌려 결과를 돌려준다."""
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/test_twin.py'], cwd=ROOT,
                       capture_output=True, text=True, timeout=600)
    return (r.stdout[-3000:] + r.stderr[-1000:]).strip()


if __name__ == '__main__':
    mcp.run()
