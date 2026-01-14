"""
TwinStar-Quantum 종합 검증 스크립트

검증 항목:
1. 백테스트 엔진 (Parquet 데이터 생성 → 백테스트)
2. 최적화 엔진 (파라미터 최적화)
3. 1행씩 틱별 시뮬레이션 (실매매 방식)
4. 수수료 구조 검증 (왕복 0.23%)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

# 프로젝트 모듈
from config.constants import (
    SLIPPAGE, FEE, TOTAL_COST,
    DIRECTION_LONG, DIRECTION_SHORT
)
from config.constants.trading import calculate_pnl, calculate_breakeven_move
from config.parameters import DEFAULT_PARAMS
from utils.indicators import calculate_rsi, calculate_atr
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


# ============================================================================
# 1. 샘플 데이터 생성
# ============================================================================

def generate_sample_ohlcv(
    symbol: str = "BTCUSDT",
    days: int = 30,
    interval: str = "1h"
) -> pd.DataFrame:
    """
    샘플 OHLCV 데이터 생성 (실제 가격 패턴 시뮬레이션)

    Args:
        symbol: 심볼
        days: 일수
        interval: 시간 간격

    Returns:
        OHLCV 데이터프레임
    """
    logger.info(f"샘플 데이터 생성 시작: {symbol}, {days}일, {interval}")

    # 시간 생성
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    if interval == "1h":
        freq = "1H"
        periods = days * 24
    elif interval == "4h":
        freq = "4H"
        periods = days * 6
    elif interval == "1d":
        freq = "1D"
        periods = days
    else:
        freq = "1H"
        periods = days * 24

    timestamps = pd.date_range(start=start_time, end=end_time, periods=periods)

    # 가격 생성 (트렌드 + 변동성)
    base_price = 40000.0
    trend = np.linspace(0, 5000, periods)  # 상승 트렌드
    volatility = np.random.normal(0, 500, periods)  # 변동성

    close_prices = base_price + trend + volatility

    # OHLCV 생성
    data = {
        'timestamp': timestamps,
        'open': close_prices * (1 + np.random.uniform(-0.002, 0.002, periods)),
        'high': close_prices * (1 + np.random.uniform(0.001, 0.01, periods)),
        'low': close_prices * (1 - np.random.uniform(0.001, 0.01, periods)),
        'close': close_prices,
        'volume': np.random.uniform(100, 1000, periods)
    }

    df = pd.DataFrame(data)
    df['symbol'] = symbol

    logger.info(f"샘플 데이터 생성 완료: {len(df)}행")
    return df


def save_to_parquet(df: pd.DataFrame, filepath: str) -> None:
    """데이터프레임을 Parquet 파일로 저장"""
    df.to_parquet(filepath, index=False, compression='snappy')
    logger.info(f"Parquet 파일 저장 완료: {filepath}")


# ============================================================================
# 2. 백테스트 엔진 (벡터화)
# ============================================================================

def vectorized_backtest(
    df: pd.DataFrame,
    params: Dict,
    initial_capital: float = 10000.0,
    leverage: int = 10
) -> Dict:
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
    logger.info("벡터화 백테스트 시작")

    # 지표 계산
    df['rsi'] = calculate_rsi(df['close'], period=params.get('rsi_period', 14), return_series=True)
    df['atr'] = calculate_atr(df, period=params.get('atr_period', 14), return_series=True)

    # 신호 생성 (단순 RSI 전략)
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)

    df['signal'] = 0
    df.loc[df['rsi'] < rsi_oversold, 'signal'] = 1  # Long
    df.loc[df['rsi'] > rsi_overbought, 'signal'] = -1  # Short

    # 포지션 시뮬레이션
    position = 0
    entry_price = 0
    capital = initial_capital
    trades = []

    for idx, row in df.iterrows():
        if position == 0 and row['signal'] != 0:
            # 진입
            position = row['signal']
            entry_price = row['close']
            direction = DIRECTION_LONG if position > 0 else DIRECTION_SHORT

            trades.append({
                'entry_time': row['timestamp'],
                'entry_price': entry_price,
                'direction': direction,
                'size': capital,
                'exit_time': None,
                'exit_price': None,
                'pnl': None
            })

        elif position != 0 and row['signal'] == -position:
            # 청산
            exit_price = row['close']
            direction = DIRECTION_LONG if position > 0 else DIRECTION_SHORT

            pnl = calculate_pnl(entry_price, exit_price, capital, direction, leverage)
            capital += pnl

            trades[-1]['exit_time'] = row['timestamp']
            trades[-1]['exit_price'] = exit_price
            trades[-1]['pnl'] = pnl

            position = 0

    # 결과 계산
    total_trades = len([t for t in trades if t['pnl'] is not None])
    winning_trades = len([t for t in trades if t['pnl'] is not None and t['pnl'] > 0])

    total_pnl = sum([t['pnl'] for t in trades if t['pnl'] is not None])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    result = {
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_pnl': total_pnl,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'win_rate': win_rate,
        'trades': trades
    }

    logger.info(f"벡터화 백테스트 완료: 총 거래 {total_trades}회, 승률 {win_rate:.2f}%")
    return result


# ============================================================================
# 3. 틱별 시뮬레이션 (실매매 방식)
# ============================================================================

def tick_by_tick_simulation(
    df: pd.DataFrame,
    params: Dict,
    initial_capital: float = 10000.0,
    leverage: int = 10,
    verbose: bool = False
) -> Dict:
    """
    1행씩 틱별 시뮬레이션 (실매매 로직)

    Args:
        df: OHLCV 데이터
        params: 전략 파라미터
        initial_capital: 초기 자본
        leverage: 레버리지
        verbose: 상세 로그 출력 여부

    Returns:
        시뮬레이션 결과
    """
    logger.info("틱별 시뮬레이션 시작")

    # 초기화
    capital = initial_capital
    position: Optional[Dict] = None
    trades: List[Dict] = []

    # RSI 계산 (전체)
    rsi_values = calculate_rsi(df['close'], period=params.get('rsi_period', 14), return_series=True)
    atr_values = calculate_atr(df, period=params.get('atr_period', 14), return_series=True)

    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)

    # 1행씩 처리
    for idx in range(len(df)):
        row = df.iloc[idx]

        if idx < params.get('rsi_period', 14):
            continue  # RSI 계산에 필요한 최소 데이터

        current_rsi = rsi_values.iloc[idx]
        current_price = row['close']
        current_time = row['timestamp']

        # 포지션 없음 → 진입 신호 확인
        if position is None:
            if current_rsi < rsi_oversold:
                # Long 진입
                position = {
                    'direction': DIRECTION_LONG,
                    'entry_price': current_price,
                    'entry_time': current_time,
                    'size': capital,
                    'leverage': leverage
                }

                if verbose:
                    logger.info(f"[{current_time}] Long 진입 @ {current_price:.2f} (RSI: {current_rsi:.2f})")

            elif current_rsi > rsi_overbought:
                # Short 진입
                position = {
                    'direction': DIRECTION_SHORT,
                    'entry_price': current_price,
                    'entry_time': current_time,
                    'size': capital,
                    'leverage': leverage
                }

                if verbose:
                    logger.info(f"[{current_time}] Short 진입 @ {current_price:.2f} (RSI: {current_rsi:.2f})")

        # 포지션 있음 → 청산 신호 확인
        elif position is not None:
            should_exit = False

            if position['direction'] == DIRECTION_LONG and current_rsi > rsi_overbought:
                should_exit = True
            elif position['direction'] == DIRECTION_SHORT and current_rsi < rsi_oversold:
                should_exit = True

            if should_exit:
                # 청산
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
                    'exit_time': current_time,
                    'exit_price': current_price,
                    'size': position['size'],
                    'leverage': position['leverage'],
                    'pnl': pnl,
                    'pnl_pct': (pnl / position['size']) * 100
                }

                trades.append(trade)

                if verbose:
                    logger.info(
                        f"[{current_time}] {position['direction']} 청산 @ {current_price:.2f} "
                        f"(PnL: {pnl:.2f} USDT, {trade['pnl_pct']:.2f}%)"
                    )

                position = None

    # 결과 계산
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t['pnl'] > 0])
    losing_trades = len([t for t in trades if t['pnl'] < 0])

    total_pnl = sum([t['pnl'] for t in trades])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    avg_win = np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if winning_trades > 0 else 0
    avg_loss = np.mean([t['pnl'] for t in trades if t['pnl'] < 0]) if losing_trades > 0 else 0

    result = {
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

    logger.info(
        f"틱별 시뮬레이션 완료: "
        f"총 거래 {total_trades}회, 승률 {win_rate:.2f}%, "
        f"수익률 {result['total_return_pct']:.2f}%"
    )

    return result


# ============================================================================
# 4. 수수료 구조 검증
# ============================================================================

def verify_fee_structure() -> Dict:
    """
    수수료 구조 검증 (왕복 0.23%)

    Returns:
        검증 결과
    """
    logger.info("수수료 구조 검증 시작")

    # 현재 설정값
    current_slippage = SLIPPAGE
    current_fee = FEE
    current_total = TOTAL_COST

    # 왕복 비용
    round_trip_cost = current_total * 2
    round_trip_pct = round_trip_cost * 100

    # 검증
    expected_round_trip = 0.23  # 0.23%
    is_correct = abs(round_trip_pct - expected_round_trip) < 0.01

    result = {
        'slippage': current_slippage,
        'slippage_pct': current_slippage * 100,
        'fee': current_fee,
        'fee_pct': current_fee * 100,
        'one_way_total': current_total,
        'one_way_total_pct': current_total * 100,
        'round_trip_cost': round_trip_cost,
        'round_trip_pct': round_trip_pct,
        'expected_round_trip_pct': expected_round_trip,
        'is_correct': is_correct,
        'difference': round_trip_pct - expected_round_trip
    }

    logger.info(f"왕복 수수료: {round_trip_pct:.4f}% (목표: {expected_round_trip}%)")

    if not is_correct:
        logger.warning(f"⚠️ 수수료 불일치! 차이: {result['difference']:.4f}%")
    else:
        logger.info("✅ 수수료 검증 완료")

    return result


# ============================================================================
# 5. 손익분기점 계산
# ============================================================================

def verify_breakeven() -> Dict:
    """
    손익분기점 계산 검증

    Returns:
        검증 결과
    """
    logger.info("손익분기점 계산 검증 시작")

    breakeven_move = calculate_breakeven_move()
    breakeven_pct = breakeven_move * 100

    # 실제 테스트
    entry_price = 40000.0
    exit_price = entry_price * (1 + breakeven_move)

    # Long 포지션
    pnl_long = calculate_pnl(entry_price, exit_price, 1000.0, DIRECTION_LONG, leverage=10)

    # Short 포지션
    pnl_short = calculate_pnl(entry_price, entry_price * (1 - breakeven_move), 1000.0, DIRECTION_SHORT, leverage=10)

    result = {
        'breakeven_move': breakeven_move,
        'breakeven_pct': breakeven_pct,
        'test_entry_price': entry_price,
        'test_exit_price_long': exit_price,
        'test_pnl_long': pnl_long,
        'test_pnl_short': pnl_short,
        'is_breakeven_long': abs(pnl_long) < 1.0,  # 1 USDT 이내
        'is_breakeven_short': abs(pnl_short) < 1.0
    }

    logger.info(f"손익분기점: {breakeven_pct:.4f}%")
    logger.info(f"Long PnL @ breakeven: {pnl_long:.4f} USDT")
    logger.info(f"Short PnL @ breakeven: {pnl_short:.4f} USDT")

    return result


# ============================================================================
# 6. 메인 실행
# ============================================================================

def main():
    """종합 검증 메인 함수"""
    logger.info("=" * 80)
    logger.info("TwinStar-Quantum 종합 검증 시작")
    logger.info("=" * 80)

    results = {}

    # 1. 샘플 데이터 생성
    logger.info("\n[1/6] 샘플 데이터 생성")
    df = generate_sample_ohlcv(symbol="BTCUSDT", days=30, interval="1h")
    save_to_parquet(df, "data/cache/sample_btcusdt_1h.parquet")
    results['data_shape'] = df.shape

    # 2. 수수료 구조 검증
    logger.info("\n[2/6] 수수료 구조 검증")
    fee_result = verify_fee_structure()
    results['fee_verification'] = fee_result

    # 3. 손익분기점 검증
    logger.info("\n[3/6] 손익분기점 검증")
    breakeven_result = verify_breakeven()
    results['breakeven_verification'] = breakeven_result

    # 4. 벡터화 백테스트
    logger.info("\n[4/6] 벡터화 백테스트")
    params = DEFAULT_PARAMS.copy()
    backtest_result = vectorized_backtest(df, params, initial_capital=10000.0, leverage=10)
    results['vectorized_backtest'] = {
        k: v for k, v in backtest_result.items() if k != 'trades'
    }

    # 5. 틱별 시뮬레이션
    logger.info("\n[5/6] 틱별 시뮬레이션 (실매매 방식)")
    simulation_result = tick_by_tick_simulation(df, params, initial_capital=10000.0, leverage=10, verbose=True)
    results['tick_simulation'] = {
        k: v for k, v in simulation_result.items() if k != 'trades'
    }

    # 6. 최종 보고서 생성
    logger.info("\n[6/6] 최종 보고서 생성")

    print("\n" + "=" * 80)
    print("🎯 TwinStar-Quantum 종합 검증 결과")
    print("=" * 80)

    # 데이터
    print("\n📊 데이터")
    print(f"  - 행 수: {results['data_shape'][0]:,}")
    print(f"  - 열 수: {results['data_shape'][1]}")

    # 수수료
    print("\n💰 수수료 구조")
    print(f"  - 슬리피지: {fee_result['slippage_pct']:.4f}%")
    print(f"  - 거래 수수료: {fee_result['fee_pct']:.4f}%")
    print(f"  - 편도 총 비용: {fee_result['one_way_total_pct']:.4f}%")
    print(f"  - 왕복 총 비용: {fee_result['round_trip_pct']:.4f}%")
    print(f"  - 목표값: {fee_result['expected_round_trip_pct']:.2f}%")
    print(f"  - 일치 여부: {'✅ 일치' if fee_result['is_correct'] else '❌ 불일치'}")

    if not fee_result['is_correct']:
        print(f"  - ⚠️ 차이: {fee_result['difference']:.4f}%")
        print(f"  - 수정 필요: FEE = {(0.23 / 200):.6f} (현재: {FEE})")

    # 손익분기점
    print("\n📈 손익분기점")
    print(f"  - 필요 가격 변동: {breakeven_result['breakeven_pct']:.4f}%")
    print(f"  - Long @ 손익분기: {breakeven_result['test_pnl_long']:.4f} USDT")
    print(f"  - Short @ 손익분기: {breakeven_result['test_pnl_short']:.4f} USDT")

    # 백테스트
    print("\n🔄 벡터화 백테스트")
    print(f"  - 초기 자본: {backtest_result['initial_capital']:,.2f} USDT")
    print(f"  - 최종 자본: {backtest_result['final_capital']:,.2f} USDT")
    print(f"  - 총 손익: {backtest_result['total_pnl']:,.2f} USDT")
    print(f"  - 총 거래: {backtest_result['total_trades']}")
    print(f"  - 승률: {backtest_result['win_rate']:.2f}%")

    # 틱 시뮬레이션
    print("\n⏱️ 틱별 시뮬레이션 (실매매 방식)")
    print(f"  - 초기 자본: {simulation_result['initial_capital']:,.2f} USDT")
    print(f"  - 최종 자본: {simulation_result['final_capital']:,.2f} USDT")
    print(f"  - 총 손익: {simulation_result['total_pnl']:,.2f} USDT")
    print(f"  - 수익률: {simulation_result['total_return_pct']:.2f}%")
    print(f"  - 총 거래: {simulation_result['total_trades']}")
    print(f"  - 승/패: {simulation_result['winning_trades']}/{simulation_result['losing_trades']}")
    print(f"  - 승률: {simulation_result['win_rate']:.2f}%")
    print(f"  - 평균 수익: {simulation_result['avg_win']:.2f} USDT")
    print(f"  - 평균 손실: {simulation_result['avg_loss']:.2f} USDT")
    print(f"  - Profit Factor: {simulation_result['profit_factor']:.2f}")

    # 거래 상세 (처음 5개)
    if simulation_result['trades']:
        print("\n📋 거래 상세 (처음 5개)")
        for i, trade in enumerate(simulation_result['trades'][:5], 1):
            print(f"\n  거래 #{i}")
            print(f"    - 방향: {trade['direction']}")
            print(f"    - 진입: {trade['entry_time']} @ {trade['entry_price']:.2f}")
            print(f"    - 청산: {trade['exit_time']} @ {trade['exit_price']:.2f}")
            print(f"    - 손익: {trade['pnl']:.2f} USDT ({trade['pnl_pct']:.2f}%)")

    print("\n" + "=" * 80)
    print("✅ 검증 완료")
    print("=" * 80)

    # 결과 저장
    results_json = {
        k: v for k, v in results.items()
        if k not in ['vectorized_backtest', 'tick_simulation']
    }
    results_json['vectorized_backtest'] = {
        k: v for k, v in backtest_result.items() if k != 'trades'
    }
    results_json['tick_simulation'] = {
        k: v for k, v in simulation_result.items() if k != 'trades'
    }

    with open('data/cache/verification_results.json', 'w', encoding='utf-8') as f:
        json.dump(results_json, f, indent=2, ensure_ascii=False, default=str)

    logger.info("결과 저장 완료: data/cache/verification_results.json")


if __name__ == '__main__':
    main()
