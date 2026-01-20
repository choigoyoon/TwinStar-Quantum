"""
프리셋 백테스트 검증 스크립트 (v7.23)

사용자가 제공한 MACD vs ADX 비교 결과를 검증합니다:

MACD 전략: 승률 88.3%, MDD 3.52%, Sharpe 31.81, PF 15.34
ADX 전략: 승률 93.8%, MDD 3.44%, Sharpe 34.69, PF 24.66
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
import pandas as pd

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators
from utils.metrics import calculate_backtest_metrics


def load_preset(filepath: str) -> Dict[str, Any]:
    """프리셋 JSON 파일 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_preset_backtest(
    exchange: str,
    symbol: str,
    timeframe: str,
    params: Dict[str, Any],
    strategy_type: str = 'macd'
) -> Dict[str, Any]:
    """
    프리셋 파라미터로 백테스트 실행

    Args:
        exchange: 거래소 ('bybit')
        symbol: 심볼 ('BTCUSDT')
        timeframe: 타임프레임 ('1h')
        params: 파라미터 딕셔너리
        strategy_type: 전략 타입 ('macd' or 'adx')

    Returns:
        백테스트 결과 딕셔너리
    """
    print(f"\n{'='*80}")
    print(f"백테스트 실행: {strategy_type.upper()} 전략")
    print(f"거래소: {exchange}, 심볼: {symbol}, 타임프레임: {timeframe}")
    print(f"파라미터: {params}")
    print(f"{'='*80}\n")

    # 1. 데이터 로드
    dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})
    dm.load_historical()

    # Optional 체크 (Pyright 에러 수정)
    if dm.df_entry_full is None:
        raise ValueError("데이터가 비어 있습니다. 먼저 데이터를 다운로드하세요.")

    df_15m = dm.df_entry_full.copy()
    if df_15m.empty:
        raise ValueError("데이터가 비어 있습니다. 먼저 데이터를 다운로드하세요.")

    # 2. 타임프레임 리샘플링 (15m → 1h)
    if timeframe == '1h':
        # 직접 리샘플링 (resample_data 메서드 없음)
        df_1h = df_15m.resample('1h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
    else:
        df_1h = df_15m.copy()

    # 3. 지표 추가
    add_all_indicators(df_1h, inplace=True)

    print(f"데이터 범위: {df_1h.index[0]} ~ {df_1h.index[-1]}")
    print(f"총 캔들 수: {len(df_1h):,}개\n")

    # 4. 전략 초기화
    strategy = AlphaX7Core(use_mtf=True, strategy_type=strategy_type)

    # 5. 백테스트 실행
    leverage = params.get('leverage', 1)

    result = strategy.run_backtest(
        df_pattern=df_1h,
        df_entry=df_1h,
        slippage=0.0005,  # 0.05%
        atr_mult=params.get('atr_mult'),
        trail_start_r=params.get('trail_start_r'),
        trail_dist_r=params.get('trail_dist_r'),
        entry_validity_hours=params.get('entry_validity_hours'),
        filter_tf=params.get('filter_tf'),
        # MACD 파라미터
        macd_fast=params.get('macd_fast'),
        macd_slow=params.get('macd_slow'),
        macd_signal=params.get('macd_signal'),
        # ADX 파라미터
        adx_period=params.get('adx_period'),
        adx_threshold=params.get('adx_threshold'),
    )

    # 6. 거래 내역 추출
    trades = result.get('trades', [])
    if not trades:
        print("⚠️ 거래가 없습니다!\n")
        return {
            'total_trades': 0,
            'win_rate': 0,
            'mdd': 0,
            'sharpe_ratio': 0,
            'profit_factor': 0
        }

    # 7. 메트릭 계산
    metrics = calculate_backtest_metrics(trades, leverage=leverage, capital=100.0)

    # 8. 결과 출력
    print(f"\n{'='*80}")
    print(f"백테스트 결과 ({strategy_type.upper()})")
    print(f"{'='*80}")
    print(f"총 거래: {metrics['total_trades']:,}회")
    print(f"승률: {metrics['win_rate']:.1f}%")
    print(f"MDD: {metrics['mdd']:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"{'='*80}\n")

    return metrics


def compare_presets(
    preset_macd_path: str,
    preset_adx_path: str,
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    timeframe: str = '1h'
) -> None:
    """
    MACD vs ADX 프리셋 비교

    Args:
        preset_macd_path: MACD 프리셋 경로
        preset_adx_path: ADX 프리셋 경로
        exchange: 거래소
        symbol: 심볼
        timeframe: 타임프레임
    """
    print(f"\n{'#'*80}")
    print(f"# 프리셋 백테스트 검증 (v7.23)")
    print(f"# MACD vs ADX 전략 비교")
    print(f"{'#'*80}\n")

    # 1. MACD 프리셋 로드 & 백테스트
    preset_macd = load_preset(preset_macd_path)
    params_macd = preset_macd.get('params', {})

    # MACD 기본 파라미터 추가 (프리셋에 없으면)
    if 'macd_fast' not in params_macd:
        params_macd.update({
            'macd_fast': 6,
            'macd_slow': 18,
            'macd_signal': 7
        })

    result_macd = run_preset_backtest(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        params=params_macd,
        strategy_type='macd'
    )

    # 2. ADX 프리셋 로드 & 백테스트
    preset_adx = load_preset(preset_adx_path)
    params_adx = preset_adx.get('params', {})

    # ADX 기본 파라미터 추가 (프리셋에 없으면)
    if 'adx_period' not in params_adx:
        params_adx.update({
            'adx_period': 14,
            'adx_threshold': 25.0
        })

    result_adx = run_preset_backtest(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        params=params_adx,
        strategy_type='adx'
    )

    # 3. 비교 결과 출력
    print(f"\n{'='*80}")
    print(f"최종 비교 결과")
    print(f"{'='*80}")
    print(f"{'지표':<20} {'MACD':>15} {'ADX':>15} {'우위':>10} {'개선폭':>12}")
    print(f"{'-'*80}")

    # 승률
    win_rate_diff = result_adx['win_rate'] - result_macd['win_rate']
    win_rate_pct = (win_rate_diff / result_macd['win_rate'] * 100) if result_macd['win_rate'] > 0 else 0
    winner_wr = 'ADX' if win_rate_diff > 0 else 'MACD'
    print(f"{'승률':<20} {result_macd['win_rate']:>14.1f}% {result_adx['win_rate']:>14.1f}% {winner_wr:>10} {win_rate_pct:>11.1f}%")

    # MDD
    mdd_diff = result_adx['mdd'] - result_macd['mdd']
    mdd_pct = (mdd_diff / result_macd['mdd'] * 100) if result_macd['mdd'] > 0 else 0
    winner_mdd = 'ADX' if mdd_diff < 0 else 'MACD'
    print(f"{'MDD':<20} {result_macd['mdd']:>14.2f}% {result_adx['mdd']:>14.2f}% {winner_mdd:>10} {mdd_pct:>11.1f}%")

    # Sharpe
    sharpe_diff = result_adx['sharpe_ratio'] - result_macd['sharpe_ratio']
    sharpe_pct = (sharpe_diff / result_macd['sharpe_ratio'] * 100) if result_macd['sharpe_ratio'] > 0 else 0
    winner_sharpe = 'ADX' if sharpe_diff > 0 else 'MACD'
    print(f"{'Sharpe Ratio':<20} {result_macd['sharpe_ratio']:>15.2f} {result_adx['sharpe_ratio']:>15.2f} {winner_sharpe:>10} {sharpe_pct:>11.1f}%")

    # Profit Factor
    pf_diff = result_adx['profit_factor'] - result_macd['profit_factor']
    pf_pct = (pf_diff / result_macd['profit_factor'] * 100) if result_macd['profit_factor'] > 0 else 0
    winner_pf = 'ADX' if pf_diff > 0 else 'MACD'
    print(f"{'Profit Factor':<20} {result_macd['profit_factor']:>15.2f} {result_adx['profit_factor']:>15.2f} {winner_pf:>10} {pf_pct:>11.1f}%")

    # 총 거래
    trades_diff = result_adx['total_trades'] - result_macd['total_trades']
    trades_pct = (trades_diff / result_macd['total_trades'] * 100) if result_macd['total_trades'] > 0 else 0
    winner_trades = 'MACD' if trades_diff < 0 else 'ADX'
    print(f"{'총 거래':<20} {result_macd['total_trades']:>14,}회 {result_adx['total_trades']:>14,}회 {winner_trades:>10} {trades_pct:>11.1f}%")

    print(f"{'='*80}\n")

    # 4. 사용자 제공 값과 비교
    print(f"{'='*80}")
    print(f"사용자 제공 값과 비교")
    print(f"{'='*80}")

    user_macd = {
        'win_rate': 88.3,
        'mdd': 3.52,
        'sharpe_ratio': 31.81,
        'profit_factor': 15.34,
        'total_trades': 3236
    }

    user_adx = {
        'win_rate': 93.8,
        'mdd': 3.44,
        'sharpe_ratio': 34.69,
        'profit_factor': 24.66,
        'total_trades': 2558
    }

    print(f"\n[MACD 전략 검증]")
    print(f"{'지표':<20} {'사용자 값':>15} {'검증 값':>15} {'차이':>12}")
    print(f"{'-'*80}")
    print(f"{'승률':<20} {user_macd['win_rate']:>14.1f}% {result_macd['win_rate']:>14.1f}% {result_macd['win_rate']-user_macd['win_rate']:>11.1f}%")
    print(f"{'MDD':<20} {user_macd['mdd']:>14.2f}% {result_macd['mdd']:>14.2f}% {result_macd['mdd']-user_macd['mdd']:>11.2f}%")
    print(f"{'Sharpe Ratio':<20} {user_macd['sharpe_ratio']:>15.2f} {result_macd['sharpe_ratio']:>15.2f} {result_macd['sharpe_ratio']-user_macd['sharpe_ratio']:>12.2f}")
    print(f"{'Profit Factor':<20} {user_macd['profit_factor']:>15.2f} {result_macd['profit_factor']:>15.2f} {result_macd['profit_factor']-user_macd['profit_factor']:>12.2f}")
    print(f"{'총 거래':<20} {user_macd['total_trades']:>14,}회 {result_macd['total_trades']:>14,}회 {result_macd['total_trades']-user_macd['total_trades']:>11,}회")

    print(f"\n[ADX 전략 검증]")
    print(f"{'지표':<20} {'사용자 값':>15} {'검증 값':>15} {'차이':>12}")
    print(f"{'-'*80}")
    print(f"{'승률':<20} {user_adx['win_rate']:>14.1f}% {result_adx['win_rate']:>14.1f}% {result_adx['win_rate']-user_adx['win_rate']:>11.1f}%")
    print(f"{'MDD':<20} {user_adx['mdd']:>14.2f}% {result_adx['mdd']:>14.2f}% {result_adx['mdd']-user_adx['mdd']:>11.2f}%")
    print(f"{'Sharpe Ratio':<20} {user_adx['sharpe_ratio']:>15.2f} {result_adx['sharpe_ratio']:>15.2f} {result_adx['sharpe_ratio']-user_adx['sharpe_ratio']:>12.2f}")
    print(f"{'Profit Factor':<20} {user_adx['profit_factor']:>15.2f} {result_adx['profit_factor']:>15.2f} {result_adx['profit_factor']-user_adx['profit_factor']:>12.2f}")
    print(f"{'총 거래':<20} {user_adx['total_trades']:>14,}회 {result_adx['total_trades']:>14,}회 {result_adx['total_trades']-user_adx['total_trades']:>11,}회")

    print(f"{'='*80}\n")


if __name__ == '__main__':
    # 프리셋 경로
    preset_macd = 'presets/bybit/bybit_btcusdt_optimal_20260116.json'
    preset_adx = 'presets/bybit/bybit_btcusdt_balanced_20260116.json'

    # 비교 실행
    compare_presets(
        preset_macd_path=preset_macd,
        preset_adx_path=preset_adx,
        exchange='bybit',
        symbol='BTCUSDT',
        timeframe='1h'
    )
