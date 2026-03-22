#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
원클릭 프리셋 생성기

Phase 5 최적 파라미터로 백테스트 실행 후:
1. 실제 수익률 확인
2. 목표 기준으로 5가지 프리셋 자동 생성
3. JSON 파일 저장
4. 요약 보고서 출력

사용법:
    python tools/generate_presets.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from core.optimizer import BacktestOptimizer
from utils.metrics import calculate_backtest_metrics
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def run_backtest_with_params(df: pd.DataFrame, params: dict) -> Tuple[List, dict, float]:
    """
    백테스트 실행 및 메트릭 계산

    Returns:
        (trades, metrics, total_years)
    """
    print(f"  백테스트 실행 중... (leverage={params['leverage']}x)")

    # 리샘플링
    optimizer = BacktestOptimizer(AlphaX7Core, df)
    df_pattern = optimizer._resample(df, params.get('trend_interval', '1h'))  # type: ignore[attr-defined]
    df_entry = df.copy()

    # 백테스트
    strategy = AlphaX7Core()
    trades = strategy.run_backtest(
        df_pattern=df_pattern,
        df_entry=df_entry,
        slippage=0.001,
        atr_mult=params['atr_mult'],
        trail_start_r=params['trail_start_r'],
        trail_dist_r=params['trail_dist_r'],
        entry_validity_hours=params['entry_validity_hours'],
        filter_tf=params.get('filter_tf')
    )

    if not trades or not isinstance(trades, list):
        raise ValueError("백테스트 실패")

    # 메트릭 계산
    metrics = calculate_backtest_metrics(
        trades=trades,
        leverage=params['leverage'],
        capital=100.0
    )

    # 기간 계산
    if 'timestamp' in df.columns:
        total_days = (df['timestamp'].max() - df['timestamp'].min()).days
    else:
        total_days = len(df) * 15 / (60 * 24)

    total_years = total_days / 365.25

    print(f"  [OK] 거래: {len(trades)}개, 승률: {metrics['win_rate']:.2f}%, MDD: {metrics['mdd']:.2f}%")

    return trades, metrics, total_years


def calculate_five_year_return(trades: List, total_years: float, leverage: int) -> float:
    """5년 환산 수익률 계산 (단리 기준)"""
    # 총 PnL 합산
    total_pnl = sum(t.get('pnl', 0) for t in trades)

    # leverage 적용
    total_pnl_with_leverage = total_pnl * leverage

    # 기간 대비 연 수익률
    annual_return_pct = (total_pnl_with_leverage / total_years)

    # 5년 환산 (단리)
    five_year_return_pct = annual_return_pct * 5

    return five_year_return_pct


def create_preset(name: str, params: dict, description: str) -> dict:
    """프리셋 JSON 생성"""
    return {
        "name": name,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "params": params
    }


def save_preset(preset: dict, filename: str) -> None:
    """프리셋 파일 저장"""
    presets_dir = Path('presets/bybit')
    presets_dir.mkdir(parents=True, exist_ok=True)

    filepath = presets_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(preset, f, indent=2, ensure_ascii=False)

    print(f"  [저장] {filepath}")


def main():
    print("=" * 80)
    print("원클릭 프리셋 생성기")
    print("=" * 80)
    print()

    # 1. 데이터 로드
    print("1. 데이터 로드 중...")
    dm = BotDataManager('bybit', 'BTCUSDT')
    if not dm.load_historical():
        print("[ERROR] 데이터 로드 실패")
        return

    df = dm.df_entry_full
    if df is None or df.empty:
        print("[ERROR] 데이터가 비어있습니다")
        return

    print(f"  [OK] 데이터: {len(df):,}개 캔들")

    if 'timestamp' in df.columns:
        print(f"  기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
        total_days = (df['timestamp'].max() - df['timestamp'].min()).days
    else:
        total_days = len(df) * 15 / (60 * 24)
        print(f"  기간: 약 {total_days:.0f}일 (15분봉 기준)")

    total_years = total_days / 365.25
    print(f"  총 {total_days:.0f}일 ({total_years:.2f}년)")
    print()

    # 2. Phase 5 기준 백테스트 (leverage 1x)
    print("2. Phase 5 최적 파라미터 백테스트...")
    base_params = {
        'filter_tf': '4h',
        'atr_mult': 1.5,
        'trail_start_r': 1.0,
        'trail_dist_r': 0.02,
        'entry_validity_hours': 6.0,
        'leverage': 1,
    }

    try:
        trades, metrics, _ = run_backtest_with_params(df, base_params)
        base_five_year = calculate_five_year_return(trades, total_years, base_params['leverage'])

        print()
        print(f"  5년 환산 수익률: {base_five_year:,.2f}%")
        print(f"  목표: 2,000~3,000%")
        print()

    except Exception as e:
        print(f"[ERROR] 백테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. 목표 달성 leverage 계산
    print("3. 목표 달성 leverage 계산...")
    target_leverage = 2500 / base_five_year  # 중간값 2,500%
    print(f"  목표 2,500% 달성 leverage: {target_leverage:.2f}x")
    print()

    # 4. 5가지 프리셋 정의 (승률 80%+ 목표, 거래 빈도 0.5회/일)
    print("4. 5가지 프리셋 생성 중... (승률 80%+, 빈도 0.5회/일 목표)")
    presets_config = [
        {
            "name": "optimal",
            "description": "최적형 - 모든 목표 달성 (추천)",
            "params": {
                'filter_tf': '12h',          # 6h → 12h (강한 추세만)
                'atr_mult': 1.5,             # 1.2 → 1.5 (표준 손절)
                'trail_start_r': 1.0,
                'trail_dist_r': 0.02,
                'entry_validity_hours': 48.0, # 12 → 48 (중복 진입 방지)
                'leverage': round(target_leverage * 1.0, 2),
            }
        },
        {
            "name": "balanced",
            "description": "균형형 - Phase 5 개선",
            "params": {
                'filter_tf': '6h',           # 4h → 6h
                'atr_mult': 1.5,             # 1.25 → 1.5
                'trail_start_r': 1.0,
                'trail_dist_r': 0.02,
                'entry_validity_hours': 24.0, # 8 → 24
                'leverage': round(target_leverage * 1.1, 2),
            }
        },
        {
            "name": "conservative",
            "description": "보수형 - 안정성 최우선",
            "params": {
                'filter_tf': '1d',           # 12h → 1d (하루 단위)
                'atr_mult': 1.5,
                'trail_start_r': 1.0,
                'trail_dist_r': 0.015,
                'entry_validity_hours': 72.0, # 24 → 72 (3일)
                'leverage': round(target_leverage * 0.85, 2),
            }
        },
        {
            "name": "aggressive",
            "description": "공격형 - 고수익 추구",
            "params": {
                'filter_tf': '6h',           # 4h → 6h
                'atr_mult': 1.8,
                'trail_start_r': 1.2,        # 1.3 → 1.2
                'trail_dist_r': 0.03,        # 0.04 → 0.03
                'entry_validity_hours': 24.0, # 6 → 24
                'leverage': round(target_leverage * 1.15, 2), # 1.2 → 1.15
            }
        },
        {
            "name": "highfreq",
            "description": "빈도형 - 적당한 빈도 + 고승률",
            "params": {
                'filter_tf': '4h',           # 2h → 4h
                'atr_mult': 1.5,             # 1.0 → 1.5
                'trail_start_r': 1.0,
                'trail_dist_r': 0.02,        # 0.015 → 0.02
                'entry_validity_hours': 12.0, # 6 → 12
                'leverage': round(target_leverage * 1.3, 2),
            }
        },
    ]

    # 5. 각 프리셋 백테스트 및 저장
    results = []

    for config in presets_config:
        print()
        print(f"[{config['name'].upper()}] {config['description']}")

        try:
            trades, metrics, _ = run_backtest_with_params(df, config['params'])
            five_year = calculate_five_year_return(trades, total_years, config['params']['leverage'])

            # 목표 달성 체크
            trades_per_day = metrics['total_trades'] / total_days

            win_rate_ok = metrics['win_rate'] >= 80
            mdd_ok = metrics['mdd'] <= 20
            freq_ok = trades_per_day >= 0.5
            return_ok = 2000 <= five_year <= 3000

            print(f"  승률: {metrics['win_rate']:.2f}% {'[OK]' if win_rate_ok else '[FAIL]'}")
            print(f"  MDD: {metrics['mdd']:.2f}% {'[OK]' if mdd_ok else '[FAIL]'}")
            print(f"  매매: {trades_per_day:.2f}회/일 {'[OK]' if freq_ok else '[FAIL]'}")
            print(f"  5년: {five_year:,.2f}% {'[OK]' if return_ok else '[FAIL]'}")

            # 프리셋 생성 및 저장
            preset = create_preset(
                name=f"Bybit BTC/USDT - {config['description']}",
                params=config['params'],
                description=config['description']
            )

            filename = f"bybit_btcusdt_{config['name']}_20260116.json"
            save_preset(preset, filename)

            results.append({
                'name': config['name'],
                'win_rate': metrics['win_rate'],
                'mdd': metrics['mdd'],
                'trades_per_day': trades_per_day,
                'five_year_return': five_year,
                'all_ok': win_rate_ok and mdd_ok and freq_ok and return_ok
            })

        except Exception as e:
            print(f"  [ERROR] 실패: {e}")
            results.append({
                'name': config['name'],
                'error': str(e)
            })

    # 6. 요약 보고서
    print()
    print("=" * 80)
    print("요약 보고서")
    print("=" * 80)
    print()
    print(f"{'프리셋':<15} {'승률':<10} {'MDD':<10} {'매매/일':<10} {'5년수익':<15} {'달성'}")
    print("-" * 80)

    for r in results:
        if 'error' in r:
            print(f"{r['name']:<15} [ERROR]")
        else:
            status = '[OK]' if r['all_ok'] else '[FAIL]'
            print(f"{r['name']:<15} {r['win_rate']:>6.2f}%   {r['mdd']:>6.2f}%   {r['trades_per_day']:>6.2f}     {r['five_year_return']:>10,.0f}%   {status}")

    print()
    print(f"프리셋 저장 위치: presets/bybit/")
    print()
    print("=" * 80)
    print("완료!")
    print("=" * 80)


if __name__ == '__main__':
    main()
