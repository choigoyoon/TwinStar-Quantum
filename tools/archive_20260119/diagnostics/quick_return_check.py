#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
빠른 수익률 확인 스크립트

Phase 5 최적 파라미터로 백테스트 실행 후:
- 총 수익률
- 연 수익률
- 5년 환산 수익률
확인
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def main():
    print("=" * 80)
    print("Phase 5 최적 파라미터 수익률 확인")
    print("=" * 80)
    print()

    # 1. 데이터 로드
    print("데이터 로드 중...")
    dm = BotDataManager('bybit', 'BTCUSDT')
    if not dm.load_historical():
        print("[ERROR] 데이터 로드 실패")
        return

    df = dm.df_entry_full
    if df is None or df.empty:
        print("데이터가 비어있습니다")
        return

    print(f"[OK] 데이터: {len(df):,}개 캔들")

    # timestamp 컬럼 사용
    if 'timestamp' in df.columns:
        start_date = df['timestamp'].min()
        end_date = df['timestamp'].max()
        print(f"   기간: {start_date} ~ {end_date}")
        total_days = (end_date - start_date).days
    else:
        # 15분봉 기준 계산
        total_days = len(df) * 15 / (60 * 24)
        print(f"   기간: 약 {total_days:.0f}일 (15분봉 {len(df):,}개 기준)")

    total_years = total_days / 365.25
    print(f"   총 {total_days:.0f}일 ({total_years:.2f}년)")
    print()

    # 2. Phase 5 최적 파라미터
    params = {
        'filter_tf': '4h',
        'atr_mult': 1.5,
        'trail_start_r': 1.0,
        'trail_dist_r': 0.02,
        'entry_validity_hours': 6.0,
        'leverage': 1,
    }

    print("파라미터:")
    for k, v in params.items():
        print(f"  {k}: {v}")
    print()

    # 3. 데이터 리샘플링
    from core.optimizer import BacktestOptimizer
    optimizer = BacktestOptimizer(AlphaX7Core, df)

    # df_pattern (trend_interval=1h)
    df_pattern = optimizer._resample(df, params.get('trend_interval', '1h'))  # type: ignore[attr-defined]
    # df_entry (15m 그대로)
    df_entry = df.copy()

    print(f"df_pattern: {len(df_pattern):,}개 캔들")
    print(f"df_entry: {len(df_entry):,}개 캔들")
    print()

    # 4. 백테스트 실행
    print("백테스트 실행 중...")
    try:
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
            print(f"[ERROR] 백테스트 실패 - trades: {type(trades)}")
            return

        print(f"[OK] 거래 완료: {len(trades)}개")
    except Exception as e:
        print(f"[ERROR] 백테스트 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. 메트릭 계산
    from utils.metrics import calculate_backtest_metrics

    try:
        metrics = calculate_backtest_metrics(
            trades=trades,
            leverage=params['leverage'],
            capital=100.0
        )
        print(f"[OK] 메트릭 계산 완료")
    except Exception as e:
        print(f"[ERROR] 메트릭 계산 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("=" * 80)
    print("📊 백테스트 결과")
    print("=" * 80)

    # 기본 지표
    print(f"\n승률: {metrics.get('win_rate', 0):.2f}%")
    print(f"MDD: {metrics.get('mdd', 0):.2f}%")
    print(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
    print(f"총 거래: {metrics.get('total_trades', 0):,}회")

    # 수익률 계산
    final_capital = metrics.get('final_capital', 100.0)
    initial_capital = 100.0

    total_return_pct = ((final_capital - initial_capital) / initial_capital) * 100

    # 연 수익률 (복리)
    annual_return_pct = ((final_capital / initial_capital) ** (1 / total_years) - 1) * 100

    # 5년 환산 (복리)
    five_year_capital = initial_capital * ((1 + annual_return_pct / 100) ** 5)
    five_year_return_pct = ((five_year_capital - initial_capital) / initial_capital) * 100

    print()
    print("=" * 80)
    print("💰 수익률 분석")
    print("=" * 80)
    print(f"\n초기 자본: ${initial_capital:.2f}")
    print(f"최종 자본: ${final_capital:.2f}")
    print(f"총 수익률: {total_return_pct:,.2f}% (기간: {total_years:.2f}년)")
    print()
    print(f"📈 연 수익률 (복리): {annual_return_pct:.2f}%")
    print(f"📊 5년 환산 수익률: {five_year_return_pct:,.2f}%")
    print()

    # 목표 비교
    print("=" * 80)
    print("🎯 목표 달성도")
    print("=" * 80)
    print(f"\n승률: {metrics.get('win_rate', 0):.2f}% (목표: 80%+) {'[OK]' if metrics.get('win_rate', 0) >= 80 else '[ERROR]'}")
    print(f"MDD: {metrics.get('mdd', 0):.2f}% (목표: 20% 이하) {'[OK]' if metrics.get('mdd', 0) <= 20 else '[ERROR]'}")

    trades_per_day = metrics.get('total_trades', 0) / total_days
    print(f"매매 빈도: {trades_per_day:.2f}회/일 (목표: 0.5+) {'[OK]' if trades_per_day >= 0.5 else '[ERROR]'}")
    print(f"5년 수익률: {five_year_return_pct:,.2f}% (목표: 2000~3000%) {'[OK]' if 2000 <= five_year_return_pct <= 3000 else '[ERROR]'}")
    print()

    # Leverage 계산
    if five_year_return_pct < 2000:
        needed_leverage = 2000 / five_year_return_pct
        print(f"💡 목표 달성에 필요한 leverage: {needed_leverage:.1f}x")
    elif five_year_return_pct > 3000:
        max_leverage = 3000 / five_year_return_pct
        print(f"⚠️  목표 상한(3000%) 유지 최대 leverage: {max_leverage:.1f}x")

    print()


if __name__ == '__main__':
    main()
