"""
지정가 주문 백테스트 (v1.0 - 2026-01-19)

0.001% 오프셋 지정가 로직을 적용한 백테스트
- 롱: next_open * (1 - 0.00001) 지정가
- 숏: next_open * (1 + 0.00001) 지정가
- 체결 조건: Low <= 지정가 (롱), High >= 지정가 (숏)
- 슬리피지: 0% (지정가 보장)
- 수수료: Maker 0.02% (Bybit 기준)
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np

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


def simulate_limit_order_fills(
    df: pd.DataFrame,
    signals: List[Dict],
    limit_offset: float = 0.00001  # 0.001%
) -> List[Dict]:
    """
    지정가 주문 체결 시뮬레이션

    Args:
        df: OHLCV 데이터프레임
        signals: 신호 리스트 (run_backtest에서 생성)
        limit_offset: 지정가 오프셋 (기본값 0.001%)

    Returns:
        체결된 거래 리스트 (미체결 신호 제외)
    """
    filled_trades = []

    # timestamp → index 매핑
    ts_to_idx = {}
    for idx, row in df.iterrows():
        ts = pd.to_datetime(row['timestamp'])
        ts_to_idx[ts] = idx

    for signal in signals:
        # 신호 시간 (signal['time'])
        signal_ts = pd.to_datetime(signal['time'])
        signal_idx = ts_to_idx.get(signal_ts)

        if signal_idx is None:
            continue

        side = signal.get('type', 'Long')

        # 진입 봉 (신호 다음 봉)
        entry_idx = signal_idx + 1
        if entry_idx >= len(df):
            continue

        entry_candle = df.iloc[entry_idx]
        signal_open = entry_candle['open']

        # 지정가 계산
        if side == 'Long':
            limit_price = signal_open * (1 - limit_offset)
            # 체결 조건: Low <= 지정가
            filled = entry_candle['low'] <= limit_price
            actual_entry = limit_price if filled else None
        else:  # Short
            limit_price = signal_open * (1 + limit_offset)
            # 체결 조건: High >= 지정가
            filled = entry_candle['high'] >= limit_price
            actual_entry = limit_price if filled else None

        if filled and actual_entry is not None:
            # 신호에 실제 진입가 추가
            filled_signal = signal.copy()
            filled_signal['entry_price'] = actual_entry
            filled_signal['limit_price'] = limit_price
            filled_signal['entry_idx'] = entry_idx
            filled_trades.append(filled_signal)

    return filled_trades


def run_limit_order_backtest(
    exchange: str,
    symbol: str,
    timeframe: str,
    preset_path: str,
    limit_offset: float = 0.00001,  # 0.001%
    strategy_type: str = 'macd'
) -> Dict[str, Any]:
    """
    지정가 주문 백테스트 실행

    Args:
        exchange: 거래소 ('bybit')
        symbol: 심볼 ('BTCUSDT')
        timeframe: 타임프레임 ('1h')
        preset_path: 프리셋 파일 경로
        limit_offset: 지정가 오프셋 (기본값 0.001%)
        strategy_type: 전략 타입 ('macd' or 'adx')

    Returns:
        백테스트 결과 딕셔너리
    """
    # 프리셋 로드
    preset = load_preset(preset_path)

    if 'best_params' in preset:
        params = preset['best_params'].copy()
    else:
        params = preset.get('params', {}).copy()

    if 'meta_info' in preset and 'strategy_type' in preset['meta_info']:
        strategy_type = preset['meta_info']['strategy_type']
    elif 'strategy_type' in preset:
        strategy_type = preset['strategy_type']

    # 전략별 기본 파라미터
    if strategy_type == 'macd':
        params.setdefault('macd_fast', 6)
        params.setdefault('macd_slow', 18)
        params.setdefault('macd_signal', 7)
    elif strategy_type == 'adx':
        params.setdefault('adx_period', 14)
        params.setdefault('adx_threshold', 25.0)

    params.setdefault('atr_mult', 1.5)
    params.setdefault('filter_tf', '4h')
    params.setdefault('trail_start_r', 1.0)
    params.setdefault('trail_dist_r', 0.02)
    params.setdefault('entry_validity_hours', 24.0)
    params.setdefault('leverage', 1)

    print(f"\n{'='*80}")
    print(f"지정가 백테스트 실행: {strategy_type.upper()} 전략")
    print(f"거래소: {exchange}, 심볼: {symbol}, 타임프레임: {timeframe}")
    print(f"지정가 오프셋: ±{limit_offset*100:.3f}%")
    print(f"프리셋: {preset_path}")
    print(f"파라미터: {params}")
    print(f"{'='*80}\n")

    # 데이터 로드
    dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})
    dm.load_historical()

    if dm.df_entry_full is None:
        raise ValueError("데이터가 비어 있습니다.")

    df_15m = dm.df_entry_full.copy()
    if df_15m.empty:
        raise ValueError("데이터가 비어 있습니다.")

    # 타임프레임 리샘플링 (15m → 1h)
    if timeframe == '1h':
        if 'timestamp' in df_15m.columns:
            df_temp = df_15m.set_index('timestamp')
        else:
            df_temp = df_15m.copy()

        df_1h = df_temp.resample('1h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        df_1h.reset_index(inplace=True)
        df_1h.rename(columns={'index': 'timestamp'}, inplace=True)
    else:
        df_1h = df_15m.copy()

    # 지표 추가
    add_all_indicators(df_1h, inplace=True)

    print(f"데이터 범위: {df_1h.index[0]} ~ {df_1h.index[-1]}")
    print(f"총 캔들 수: {len(df_1h):,}개\n")

    # 전략 초기화
    strategy = AlphaX7Core(use_mtf=True, strategy_type=strategy_type)

    # leverage 추출
    leverage = params.get('leverage', 1)

    # 1단계: 시장가 백테스트 실행 (기준선)
    print("1단계: 시장가 백테스트 실행...")

    market_trades = strategy.run_backtest(
        df_pattern=df_1h,
        df_entry=df_1h,
        slippage=0.001,
        atr_mult=params.get('atr_mult'),
        trail_start_r=params.get('trail_start_r'),
        trail_dist_r=params.get('trail_dist_r'),
        entry_validity_hours=params.get('entry_validity_hours'),
        filter_tf=params.get('filter_tf'),
        macd_fast=params.get('macd_fast'),
        macd_slow=params.get('macd_slow'),
        macd_signal=params.get('macd_signal'),
        return_state=False
    )

    print(f"시장가 거래: {len(market_trades):,}개")

    # 시장가 메트릭 계산
    market_metrics = calculate_backtest_metrics(market_trades, leverage=leverage, capital=100.0)

    print(f"시장가 승률: {market_metrics['win_rate']:.1f}%")
    print(f"시장가 거래당 PnL: {market_metrics['avg_pnl']:.3f}%\n")

    # 거래를 신호로 변환 (entry_idx 기준)
    signals = []
    for trade in market_trades:
        entry_idx = trade.get('entry_idx', 0)
        if entry_idx > 0:
            signals.append({
                'type': trade.get('type', 'Long'),
                'time': df_1h.iloc[entry_idx - 1]['timestamp'],  # 신호 봉
                'entry_idx_market': entry_idx
            })

    print(f"지정가 재시뮬레이션 신호: {len(signals):,}개\n")

    if not signals:
        print("WARNING: 신호가 없습니다!\n")
        return {
            'total_signals': 0,
            'filled_trades': 0,
            'fill_rate': 0,
            'total_trades': 0,
            'win_rate': 0,
            'mdd': 0,
            'sharpe_ratio': 0,
            'profit_factor': 0
        }

    # 2단계: 지정가 체결 시뮬레이션
    print("2단계: 지정가 체결 시뮬레이션...")
    filled_trades = simulate_limit_order_fills(df_1h, signals, limit_offset)

    fill_rate = len(filled_trades) / len(signals) * 100
    print(f"체결된 거래: {len(filled_trades):,}개 / {len(signals):,}개 ({fill_rate:.1f}%)\n")

    if not filled_trades:
        print("WARNING: 체결된 거래가 없습니다!\n")
        return {
            'total_signals': len(signals),
            'filled_trades': 0,
            'fill_rate': 0,
            'total_trades': 0,
            'win_rate': 0,
            'mdd': 0,
            'sharpe_ratio': 0,
            'profit_factor': 0
        }

    # 3단계: 체결된 거래의 손익 계산
    print("3단계: 손익 계산 중...")
    trades = []

    for trade in filled_trades:
        entry_idx = trade['entry_idx']
        entry_price = trade['entry_price']
        side = trade['type']

        # ATR 기반 손절가 계산
        atr = df_1h.iloc[entry_idx].get('atr', 0)
        atr_mult = params.get('atr_mult', 1.5)

        if side == 'Long':
            stop_loss = entry_price - (atr * atr_mult)
        else:
            stop_loss = entry_price + (atr * atr_mult)

        # 트레일링 익절 시뮬레이션 (간단 버전)
        trail_start_r = params.get('trail_start_r', 1.0)
        trail_dist_r = params.get('trail_dist_r', 0.02)

        max_favorable = entry_price
        exit_price = None
        exit_idx = None

        # 진입 후 최대 500개 봉 탐색
        for i in range(entry_idx + 1, min(entry_idx + 500, len(df_1h))):
            candle = df_1h.iloc[i]
            high = candle['high']
            low = candle['low']

            if side == 'Long':
                # 손절 체크
                if low <= stop_loss:
                    exit_price = stop_loss
                    exit_idx = i
                    break

                # 트레일링 익절
                if high > max_favorable:
                    max_favorable = high

                # 익절 시작 조건
                if (max_favorable - entry_price) >= (atr * atr_mult * trail_start_r):
                    # 트레일링 손절가
                    trail_stop = max_favorable * (1 - trail_dist_r)
                    if low <= trail_stop:
                        exit_price = trail_stop
                        exit_idx = i
                        break
            else:  # Short
                # 손절 체크
                if high >= stop_loss:
                    exit_price = stop_loss
                    exit_idx = i
                    break

                # 트레일링 익절
                if low < max_favorable:
                    max_favorable = low

                # 익절 시작 조건
                if (entry_price - max_favorable) >= (atr * atr_mult * trail_start_r):
                    # 트레일링 손절가
                    trail_stop = max_favorable * (1 + trail_dist_r)
                    if high >= trail_stop:
                        exit_price = trail_stop
                        exit_idx = i
                        break

        # 출구가 없으면 마지막 봉에서 청산
        if exit_price is None:
            exit_idx = min(entry_idx + 500, len(df_1h) - 1)
            exit_price = df_1h.iloc[exit_idx]['close']

        # PnL 계산 (Maker 수수료 0.02%)
        maker_fee = 0.0002

        if side == 'Long':
            pnl = (exit_price - entry_price) / entry_price - (2 * maker_fee)
        else:
            pnl = (entry_price - exit_price) / entry_price - (2 * maker_fee)

        pnl_pct = pnl * 100

        trades.append({
            'type': side,
            'entry_idx': entry_idx,
            'exit_idx': exit_idx,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl_pct,
            'stop_loss': stop_loss,
        })

    # 4단계: 메트릭 계산
    leverage = params.get('leverage', 1)
    metrics = calculate_backtest_metrics(trades, leverage=leverage, capital=100.0)

    # 지정가 관련 통계 추가
    metrics['total_signals'] = len(signals)
    metrics['filled_trades'] = len(filled_trades)
    metrics['fill_rate'] = fill_rate

    # 5단계: 결과 출력
    print(f"\n{'='*80}")
    print(f"지정가 백테스트 결과 ({strategy_type.upper()})")
    print(f"{'='*80}")
    print(f"\n[신호 및 체결]")
    print(f"총 신호: {metrics['total_signals']:,}개")
    print(f"체결 거래: {metrics['filled_trades']:,}개")
    print(f"체결률: {metrics['fill_rate']:.1f}%")
    print(f"\n[성과 지표]")
    print(f"승률: {metrics['win_rate']:.1f}%")
    print(f"MDD: {metrics['mdd']:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"총 PnL: {metrics['total_pnl']:.2f}%")
    print(f"거래당 PnL: {metrics['avg_pnl']:.3f}%")
    print(f"{'='*80}\n")

    return metrics


def compare_market_vs_limit(
    preset_path: str,
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    timeframe: str = '1h',
    limit_offset: float = 0.00001
) -> None:
    """
    시장가 vs 지정가 백테스트 비교

    Args:
        preset_path: 프리셋 경로
        exchange: 거래소
        symbol: 심볼
        timeframe: 타임프레임
        limit_offset: 지정가 오프셋 (기본값 0.001%)
    """
    print(f"\n{'#'*80}")
    print(f"# 시장가 vs 지정가 백테스트 비교")
    print(f"# 오프셋: ±{limit_offset*100:.3f}%")
    print(f"{'#'*80}\n")

    # 지정가 백테스트
    result_limit = run_limit_order_backtest(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        preset_path=preset_path,
        limit_offset=limit_offset,
        strategy_type='macd'
    )

    # 비교 결과 출력
    print(f"\n{'='*80}")
    print(f"시장가 vs 지정가 비교 (예상)")
    print(f"{'='*80}")
    print(f"{'지표':<20} {'시장가 (기존)':>18} {'지정가 (0.001%)':>18} {'변화':>12}")
    print(f"{'-'*80}")

    # 시장가 예상값 (fill_rate_summary.md 기준)
    market_trades = 10133
    market_win_rate = 95.7
    market_pnl_per_trade = 0.40
    market_mdd = 1.24
    market_sharpe = 27.32

    # 지정가 실제값
    limit_trades = result_limit['filled_trades']
    limit_win_rate = result_limit['win_rate']
    limit_pnl_per_trade = result_limit['avg_pnl']
    limit_mdd = result_limit['mdd']
    limit_sharpe = result_limit['sharpe_ratio']

    # 거래 횟수
    trades_change = (limit_trades - market_trades) / market_trades * 100
    print(f"{'총 거래':<20} {market_trades:>17,}회 {limit_trades:>17,}회 {trades_change:>11.1f}%")

    # 승률
    wr_change = limit_win_rate - market_win_rate
    print(f"{'승률':<20} {market_win_rate:>17.1f}% {limit_win_rate:>17.1f}% {wr_change:>11.1f}%p")

    # 거래당 PnL
    pnl_change = (limit_pnl_per_trade - market_pnl_per_trade) / market_pnl_per_trade * 100
    print(f"{'거래당 PnL':<20} {market_pnl_per_trade:>17.2f}% {limit_pnl_per_trade:>17.3f}% {pnl_change:>11.1f}%")

    # MDD
    mdd_change = (limit_mdd - market_mdd) / market_mdd * 100
    print(f"{'MDD':<20} {market_mdd:>17.2f}% {limit_mdd:>17.2f}% {mdd_change:>11.1f}%")

    # Sharpe
    sharpe_change = (limit_sharpe - market_sharpe) / market_sharpe * 100
    print(f"{'Sharpe Ratio':<20} {market_sharpe:>18.2f} {limit_sharpe:>18.2f} {sharpe_change:>11.1f}%")

    print(f"{'='*80}\n")

    # 결론
    print(f"{'='*80}")
    print(f"결론")
    print(f"{'='*80}")

    if limit_trades < market_trades * 0.2:
        print("WARNING: 거래 횟수가 80% 이상 감소했습니다.")
        print(f"   체결률: {result_limit['fill_rate']:.1f}% (예상 11.1%)")
        print(f"   다중 심볼 운영 권장 (BTC + ETH + SOL 등)")

    if limit_win_rate > market_win_rate:
        print(f"OK: 승률 개선: +{wr_change:.1f}%p (진입 품질 향상)")

    if limit_pnl_per_trade > market_pnl_per_trade:
        print(f"OK: 거래당 PnL 개선: +{pnl_change:.1f}% (비용 절감)")

    if limit_sharpe > market_sharpe:
        print(f"OK: Sharpe Ratio 개선: +{sharpe_change:.1f}% (리스크 대비 수익 향상)")

    print(f"{'='*80}\n")


if __name__ == '__main__':
    # 최신 MACD 프리셋 사용
    preset_path = 'presets/coarse_fine/bybit_BTCUSDT_1h_macd_20260117_235704.json'

    # 비교 실행
    compare_market_vs_limit(
        preset_path=preset_path,
        exchange='bybit',
        symbol='BTCUSDT',
        timeframe='1h',
        limit_offset=0.00001  # 0.001%
    )
