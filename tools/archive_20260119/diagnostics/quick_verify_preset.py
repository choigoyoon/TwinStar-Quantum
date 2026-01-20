#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coarse-Fine 프리셋 백테스트 검증 스크립트

생성된 프리셋의 성능이 실제 백테스트와 일치하는지 확인
"""

import sys
from pathlib import Path

# UTF-8 출력 강제
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Root 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import argparse
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from config.constants.trading import TOTAL_COST


def verify_preset(preset_path: str, with_fees: bool = True):
    """
    프리셋 검증: 저장된 성능 vs 실제 백테스트

    Args:
        preset_path: 프리셋 파일 경로
        with_fees: 수수료 포함 여부 (기본값: True)
    """
    # 1. 프리셋 로드
    with open(preset_path, 'r', encoding='utf-8') as f:
        preset = json.load(f)

    print(f"\n{'='*80}")
    print(f"프리셋 백테스트 검증 {'(수수료 포함)' if with_fees else '(수수료 제외)'}")
    print(f"{'='*80}")
    print(f"파일: {preset_path}")

    # 2. 메타 정보
    meta = preset['meta_info']
    exchange = meta['exchange']
    symbol = meta['symbol']
    timeframe = meta['timeframe']
    strategy_type = meta['strategy_type']

    print(f"거래소: {exchange}, 심볼: {symbol}, TF: {timeframe}, 전략: {strategy_type.upper()}")

    # 3. 저장된 성능
    saved = preset['best_metrics']
    print(f"\n{'─'*80}")
    print(f"프리셋 저장 성능")
    print(f"{'─'*80}")
    print(f"승률: {saved['win_rate']:.2f}%")
    print(f"MDD: {saved['mdd']:.2f}%")
    print(f"Sharpe: {saved['sharpe_ratio']:.2f}")
    print(f"PF: {saved['profit_factor']:.2f}")
    print(f"거래수: {saved['total_trades']}회")

    # 4. 데이터 로드 및 리샘플링
    print(f"\n{'─'*80}")
    print(f"데이터 로드 및 리샘플링")
    print(f"{'─'*80}")

    # 15분봉 로드
    dm = BotDataManager(exchange, symbol, {'entry_tf': '15m'})
    dm.load_historical()
    df_15m = dm.df_entry_full

    if df_15m is None or df_15m.empty:
        print("15분봉 데이터 없음!")
        return

    print(f"15분봉: {len(df_15m):,}개")

    # 타겟 타임프레임으로 리샘플링
    if timeframe == '15m':
        df = df_15m
    else:
        from utils.data_utils import resample_data
        df = resample_data(df_15m, timeframe, add_indicators=False)

        if df is None or df.empty:
            print("리샘플링 실패!")
            return

        print(f"{timeframe} 리샘플링: {len(df):,}개 (압축률: {len(df_15m)/len(df):.1f}x)")

    print(f"최종 캔들 수: {len(df):,}개")

    # 5. 파라미터 준비
    params = preset['best_params'].copy()

    # 전략별 기본값 추가
    if strategy_type == 'macd':
        params['macd_fast'] = 6
        params['macd_slow'] = 18
        params['macd_signal'] = 7
    elif strategy_type == 'adx':
        if 'adx_period' not in params or params['adx_period'] is None:
            params['adx_period'] = 14
        if 'adx_threshold' not in params or params['adx_threshold'] is None:
            params['adx_threshold'] = 25.0

    params['trend_interval'] = timeframe
    params['strategy_type'] = strategy_type

    # 수수료 설정
    slippage_value = TOTAL_COST if with_fees else 0.0
    params['slippage'] = slippage_value

    print(f"파라미터: {params}")
    if with_fees:
        print(f"⚠️  수수료 포함: {TOTAL_COST*100:.3f}% (왕복 {TOTAL_COST*2*100:.3f}%)")

    # 6. 백테스트 실행 (BacktestOptimizer 사용)
    print(f"\n{'─'*80}")
    print(f"백테스트 실행 중...")
    print(f"{'─'*80}")

    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type=strategy_type
    )

    # 단일 파라미터를 그리드로 변환
    grid = {k: [v] for k, v in params.items()}

    # 백테스트 실행
    results = optimizer.run_optimization(
        df=df,
        grid=grid,
        max_workers=1,
        skip_filter=True  # 필터 스킵하여 단일 결과만 반환
    )

    if not results or len(results) == 0:
        print("백테스트 실패!")
        return

    backtest_result = results[0]

    # 결과 딕셔너리로 변환
    result = {
        'win_rate': backtest_result.win_rate,
        'mdd': backtest_result.max_drawdown,
        'sharpe_ratio': backtest_result.sharpe_ratio,
        'profit_factor': backtest_result.profit_factor,
        'total_trades': backtest_result.trades,
        'total_return': backtest_result.total_return
    }

    print(f"\n{'─'*80}")
    print(f"백테스트 결과")
    print(f"{'─'*80}")
    print(f"승률: {result['win_rate']:.2f}%")
    print(f"MDD: {result['mdd']:.2f}%")
    print(f"Sharpe: {result['sharpe_ratio']:.2f}")
    print(f"PF: {result['profit_factor']:.2f}")
    print(f"거래수: {result['total_trades']}회")

    # 7. 차이 계산
    print(f"\n{'='*80}")
    print(f"검증 결과")
    print(f"{'='*80}")

    diff_wr = result['win_rate'] - saved['win_rate']
    diff_mdd = result['mdd'] - saved['mdd']
    diff_sharpe = result['sharpe_ratio'] - saved['sharpe_ratio']
    diff_pf = result['profit_factor'] - saved['profit_factor']
    diff_trades = result['total_trades'] - saved['total_trades']

    print(f"{'지표':<15} {'프리셋':>12} {'백테스트':>12} {'차이':>12}")
    print(f"{'-'*80}")
    print(f"{'승률':<15} {saved['win_rate']:>11.2f}% {result['win_rate']:>11.2f}% {diff_wr:>11.2f}%")
    print(f"{'MDD':<15} {saved['mdd']:>11.2f}% {result['mdd']:>11.2f}% {diff_mdd:>11.2f}%")
    print(f"{'Sharpe':<15} {saved['sharpe_ratio']:>12.2f} {result['sharpe_ratio']:>12.2f} {diff_sharpe:>12.2f}")
    print(f"{'PF':<15} {saved['profit_factor']:>12.2f} {result['profit_factor']:>12.2f} {diff_pf:>12.2f}")
    print(f"{'거래수':<15} {saved['total_trades']:>12} {result['total_trades']:>12} {diff_trades:>12}")

    # 8. 일치 여부
    tolerance_pct = 0.1  # 0.1% 오차 허용
    tolerance_abs = 0.1  # 절대값 0.1 허용

    match_wr = abs(diff_wr) < tolerance_pct
    match_mdd = abs(diff_mdd) < tolerance_pct
    match_sharpe = abs(diff_sharpe) < tolerance_abs
    match_pf = abs(diff_pf) < tolerance_abs
    match_trades = diff_trades == 0

    print(f"\n{'='*80}")
    if match_wr and match_mdd and match_sharpe and match_pf and match_trades:
        print(f"✅ 검증 성공! 프리셋 값과 백테스트 결과 일치")
    else:
        print(f"⚠️  경고: 프리셋 값과 백테스트 결과 불일치")
        print(f"  승률: {'✓' if match_wr else '✗'}")
        print(f"  MDD: {'✓' if match_mdd else '✗'}")
        print(f"  Sharpe: {'✓' if match_sharpe else '✗'}")
        print(f"  PF: {'✓' if match_pf else '✗'}")
        print(f"  거래수: {'✓' if match_trades else '✗'}")

    # 수수료 영향 분석
    if with_fees and 'total_pnl' in saved:
        fee_impact = result['total_trades'] * TOTAL_COST * 2 * 100  # 왕복 수수료
        print(f"\n{'─'*80}")
        print(f"💰 수수료 영향 분석")
        print(f"{'─'*80}")
        print(f"거래 횟수: {result['total_trades']}회")
        print(f"왕복 수수료: {TOTAL_COST*2*100:.3f}%")
        print(f"총 수수료 영향: -{fee_impact:.2f}%")
        print(f"수수료 제외 예상 PnL: {result['total_return'] + fee_impact:.2f}%")

    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description="Coarse-Fine 프리셋 검증")
    parser.add_argument('--preset', required=True, help='프리셋 파일 경로')
    parser.add_argument('--no-fees', action='store_true', help='수수료 제외 (기본값: 포함)')

    args = parser.parse_args()
    verify_preset(args.preset, with_fees=not args.no_fees)


if __name__ == '__main__':
    main()
