"""
전체 백테스트 및 틱별 시뮬레이션 검증

1. 샘플 데이터 생성 (30일 1시간봉)
2. 벡터화 백테스트
3. 1행씩 틱별 시뮬레이션 (실매매 로직)
4. 결과 비교 및 보고서
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

# 상수 정의 (SSOT)
from config.constants import (
    SLIPPAGE, FEE, TOTAL_COST,
    DIRECTION_LONG, DIRECTION_SHORT
)


# ============================================================================
# 1. 데이터 생성
# ============================================================================

def generate_sample_data(days=30):
    """샘플 OHLCV 데이터 생성"""
    print(f"[1/5] {days}일간 샘플 데이터 생성 중...")

    periods = days * 24  # 1시간봉
    timestamps = pd.date_range(
        start=datetime.now() - timedelta(days=days),
        periods=periods,
        freq='1H'
    )

    # 가격 생성 (BTC 패턴 시뮬레이션)
    base_price = 40000.0
    trend = np.linspace(0, 5000, periods)
    noise = np.random.normal(0, 500, periods)
    close_prices = base_price + trend + noise

    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': close_prices * (1 + np.random.uniform(-0.002, 0.002, periods)),
        'high': close_prices * (1 + np.random.uniform(0.001, 0.01, periods)),
        'low': close_prices * (1 - np.random.uniform(0.001, 0.01, periods)),
        'close': close_prices,
        'volume': np.random.uniform(100, 1000, periods)
    })

    print(f"  생성 완료: {len(df)}행")
    return df


# ============================================================================
# 2. 지표 계산
# ============================================================================

def calculate_rsi(prices, period=14):
    """RSI 계산"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(high, low, close, period=14):
    """ATR 계산"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


# ============================================================================
# 3. 손익 계산
# ============================================================================

def calculate_pnl(entry_price, exit_price, size, direction, leverage=1):
    """
    손익 계산 (수수료 포함)

    Args:
        entry_price: 진입 가격
        exit_price: 청산 가격
        size: 포지션 크기 (USDT)
        direction: 방향 ('Long', 'Short')
        leverage: 레버리지

    Returns:
        순손익 (USDT)
    """
    if direction == DIRECTION_LONG:
        raw_pnl = (exit_price - entry_price) / entry_price * size * leverage
    else:
        raw_pnl = (entry_price - exit_price) / entry_price * size * leverage

    # 수수료 차감 (진입 + 청산)
    total_fee = size * TOTAL_COST * 2
    return raw_pnl - total_fee


# ============================================================================
# 4. 벡터화 백테스트
# ============================================================================

def vectorized_backtest(df, params, initial_capital=10000.0, leverage=10):
    """
    벡터화 백테스트 (전체 데이터 한 번에 처리)

    Args:
        df: OHLCV 데이터
        params: 전략 파라미터
        initial_capital: 초기 자본
        leverage: 레버리지

    Returns:
        백테스트 결과
    """
    print("[2/5] 벡터화 백테스트 실행 중...")

    # 지표 계산
    df['rsi'] = calculate_rsi(df['close'], period=params['rsi_period'])
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'], period=params['atr_period'])

    # 신호 생성
    df['signal'] = 0
    df.loc[df['rsi'] < params['rsi_oversold'], 'signal'] = 1  # Long
    df.loc[df['rsi'] > params['rsi_overbought'], 'signal'] = -1  # Short

    # 백테스트
    position = 0
    entry_price = 0
    capital = initial_capital
    trades = []

    for idx, row in df.iterrows():
        if pd.isna(row['rsi']):
            continue

        # 진입
        if position == 0 and row['signal'] != 0:
            position = row['signal']
            entry_price = row['close']
            direction = DIRECTION_LONG if position > 0 else DIRECTION_SHORT

            trades.append({
                'entry_time': row['timestamp'],
                'entry_price': entry_price,
                'direction': direction,
                'size': capital,
                'leverage': leverage
            })

        # 청산
        elif position != 0 and row['signal'] == -position:
            exit_price = row['close']
            direction = DIRECTION_LONG if position > 0 else DIRECTION_SHORT

            pnl = calculate_pnl(entry_price, exit_price, capital, direction, leverage)
            capital += pnl

            trades[-1].update({
                'exit_time': row['timestamp'],
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_pct': (pnl / trades[-1]['size']) * 100
            })

            position = 0

    # 결과 계산
    completed_trades = [t for t in trades if 'pnl' in t]
    total_trades = len(completed_trades)
    winning_trades = len([t for t in completed_trades if t['pnl'] > 0])

    total_pnl = sum([t['pnl'] for t in completed_trades])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    print(f"  완료: 총 거래 {total_trades}회, 승률 {win_rate:.2f}%")

    return {
        'method': 'vectorized',
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_pnl': total_pnl,
        'total_return_pct': (total_pnl / initial_capital) * 100,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': total_trades - winning_trades,
        'win_rate': win_rate,
        'trades': completed_trades
    }


# ============================================================================
# 5. 틱별 시뮬레이션 (실매매 방식)
# ============================================================================

def tick_by_tick_simulation(df, params, initial_capital=10000.0, leverage=10, verbose=False):
    """
    1행씩 틱별 시뮬레이션

    Args:
        df: OHLCV 데이터
        params: 전략 파라미터
        initial_capital: 초기 자본
        leverage: 레버리지
        verbose: 상세 로그

    Returns:
        시뮬레이션 결과
    """
    print("[3/5] 틱별 시뮬레이션 실행 중 (1행씩 처리)...")

    # 지표 계산
    rsi_values = calculate_rsi(df['close'], period=params['rsi_period'])

    capital = initial_capital
    position = None
    trades = []

    # 1행씩 처리
    for idx in range(len(df)):
        if idx < params['rsi_period']:
            continue  # 지표 계산을 위한 최소 데이터

        row = df.iloc[idx]
        current_rsi = rsi_values[idx]
        current_price = row['close']

        if pd.isna(current_rsi):
            continue

        # 포지션 없음 -> 진입 확인
        if position is None:
            if current_rsi < params['rsi_oversold']:
                # Long 진입
                position = {
                    'direction': DIRECTION_LONG,
                    'entry_price': current_price,
                    'entry_time': row['timestamp'],
                    'size': capital,
                    'leverage': leverage
                }

                if verbose and len(trades) < 5:
                    print(f"  [{row['timestamp']}] Long 진입 @ ${current_price:.2f}")

            elif current_rsi > params['rsi_overbought']:
                # Short 진입
                position = {
                    'direction': DIRECTION_SHORT,
                    'entry_price': current_price,
                    'entry_time': row['timestamp'],
                    'size': capital,
                    'leverage': leverage
                }

                if verbose and len(trades) < 5:
                    print(f"  [{row['timestamp']}] Short 진입 @ ${current_price:.2f}")

        # 포지션 있음 -> 청산 확인
        elif position is not None:
            should_exit = False

            if position['direction'] == DIRECTION_LONG and current_rsi > params['rsi_overbought']:
                should_exit = True
            elif position['direction'] == DIRECTION_SHORT and current_rsi < params['rsi_oversold']:
                should_exit = True

            if should_exit:
                pnl = calculate_pnl(
                    position['entry_price'],
                    current_price,
                    position['size'],
                    position['direction'],
                    position['leverage']
                )

                capital += pnl

                trade = {
                    'direction': position['direction'],
                    'entry_time': position['entry_time'],
                    'entry_price': position['entry_price'],
                    'exit_time': row['timestamp'],
                    'exit_price': current_price,
                    'size': position['size'],
                    'leverage': position['leverage'],
                    'pnl': pnl,
                    'pnl_pct': (pnl / position['size']) * 100
                }

                trades.append(trade)

                if verbose and len(trades) <= 5:
                    print(f"  [{row['timestamp']}] {position['direction']} 청산 @ ${current_price:.2f} "
                          f"(PnL: ${pnl:.2f})")

                position = None

    # 결과 계산
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t['pnl'] > 0])
    losing_trades = len([t for t in trades if t['pnl'] < 0])

    total_pnl = sum([t['pnl'] for t in trades])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    avg_win = np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if winning_trades > 0 else 0
    avg_loss = np.mean([t['pnl'] for t in trades if t['pnl'] < 0]) if losing_trades > 0 else 0

    print(f"  완료: 총 거래 {total_trades}회, 승률 {win_rate:.2f}%")

    return {
        'method': 'tick_by_tick',
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_pnl': total_pnl,
        'total_return_pct': (total_pnl / initial_capital) * 100,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
        'trades': trades
    }


# ============================================================================
# 6. 결과 비교
# ============================================================================

def compare_results(vec_result, tick_result):
    """두 결과 비교"""
    print("[4/5] 결과 비교 중...")

    print("\n" + "=" * 80)
    print("결과 비교")
    print("=" * 80)

    print(f"\n{'항목':<30} {'벡터화':<20} {'틱별':<20} {'차이':<20}")
    print("-" * 80)

    # 자본
    print(f"{'초기 자본':<30} ${vec_result['initial_capital']:>15,.2f} ${tick_result['initial_capital']:>15,.2f}")
    print(f"{'최종 자본':<30} ${vec_result['final_capital']:>15,.2f} ${tick_result['final_capital']:>15,.2f} "
          f"${vec_result['final_capital'] - tick_result['final_capital']:>15,.2f}")

    # 손익
    print(f"{'총 손익':<30} ${vec_result['total_pnl']:>15,.2f} ${tick_result['total_pnl']:>15,.2f} "
          f"${vec_result['total_pnl'] - tick_result['total_pnl']:>15,.2f}")
    print(f"{'수익률':<30} {vec_result['total_return_pct']:>14.2f}% {tick_result['total_return_pct']:>14.2f}% "
          f"{vec_result['total_return_pct'] - tick_result['total_return_pct']:>14.2f}%")

    # 거래
    print(f"{'총 거래':<30} {vec_result['total_trades']:>19} {tick_result['total_trades']:>19} "
          f"{vec_result['total_trades'] - tick_result['total_trades']:>19}")
    print(f"{'승률':<30} {vec_result['win_rate']:>14.2f}% {tick_result['win_rate']:>14.2f}% "
          f"{vec_result['win_rate'] - tick_result['win_rate']:>14.2f}%")

    print("\n" + "=" * 80)


# ============================================================================
# 7. 메인
# ============================================================================

def main():
    """메인 함수"""
    print("=" * 80)
    print("TwinStar-Quantum 전체 백테스트 검증")
    print("=" * 80)

    # 파라미터
    params = {
        'rsi_period': 14,
        'atr_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70
    }

    initial_capital = 10000.0
    leverage = 10

    # 1. 데이터 생성
    df = generate_sample_data(days=30)

    # Parquet 저장
    os.makedirs('data/cache', exist_ok=True)
    parquet_path = 'data/cache/sample_btcusdt_1h.parquet'
    df.to_parquet(parquet_path, index=False)
    print(f"  Parquet 저장: {parquet_path}")

    # 2. 벡터화 백테스트
    vec_result = vectorized_backtest(df, params, initial_capital, leverage)

    # 3. 틱별 시뮬레이션
    tick_result = tick_by_tick_simulation(df, params, initial_capital, leverage, verbose=True)

    # 4. 결과 비교
    compare_results(vec_result, tick_result)

    # 5. 결과 저장
    print("[5/5] 결과 저장 중...")

    result_summary = {
        'params': params,
        'initial_capital': initial_capital,
        'leverage': leverage,
        'data_shape': df.shape,
        'vectorized': {
            k: v for k, v in vec_result.items() if k != 'trades'
        },
        'tick_by_tick': {
            k: v for k, v in tick_result.items() if k != 'trades'
        },
        'fee_structure': {
            'slippage': SLIPPAGE,
            'fee': FEE,
            'one_way_total': TOTAL_COST,
            'round_trip_total': TOTAL_COST * 2,
            'round_trip_pct': TOTAL_COST * 2 * 100
        }
    }

    with open('data/cache/backtest_verification.json', 'w', encoding='utf-8') as f:
        json.dump(result_summary, f, indent=2, ensure_ascii=False, default=str)

    print("  결과 저장 완료: data/cache/backtest_verification.json")

    # 거래 상세 (처음 5개)
    print("\n" + "=" * 80)
    print("거래 상세 (처음 5개)")
    print("=" * 80)

    for i, trade in enumerate(tick_result['trades'][:5], 1):
        print(f"\n[거래 #{i}]")
        print(f"  방향: {trade['direction']}")
        print(f"  진입: {trade['entry_time']} @ ${trade['entry_price']:.2f}")
        print(f"  청산: {trade['exit_time']} @ ${trade['exit_price']:.2f}")
        print(f"  손익: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")

    print("\n" + "=" * 80)
    print("[OK] 전체 검증 완료")
    print("=" * 80)
    print("\n주요 결과:")
    print(f"  - 왕복 수수료: {TOTAL_COST * 2 * 100:.4f}% (목표: 0.23%)")
    print(f"  - 틱별 최종 자본: ${tick_result['final_capital']:,.2f}")
    print(f"  - 틱별 수익률: {tick_result['total_return_pct']:.2f}%")
    print(f"  - 틱별 승률: {tick_result['win_rate']:.2f}%")
    print("=" * 80)


if __name__ == '__main__':
    main()
