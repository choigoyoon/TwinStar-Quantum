"""
다중 심볼 백테스트 프레임워크 (v1.0 - 2026-01-19)

거래소/심볼 분산을 위한 동시 백테스트 시스템
"""

import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators

# 확정된 기준 파라미터 (v1.0 - 2026-01-19)
BASELINE_PARAMS = {
    'atr_mult': 1.25,
    'filter_tf': '4h',
    'trail_start_r': 0.4,
    'trail_dist_r': 0.05,
    'entry_validity_hours': 6.0,
    'leverage': 1,
    'macd_fast': 6,
    'macd_slow': 18,
    'macd_signal': 7
}

# 지정가 설정
LIMIT_OFFSET = 0.00001  # 0.001%
FEE_IMPROVEMENT = 0.27  # 시장가→지정가 수수료 절감

# 테스트 심볼 목록
TEST_SYMBOLS = [
    ('bybit', 'BTCUSDT', '1h'),
    ('bybit', 'ETHUSDT', '1h'),
    ('bybit', 'SOLUSDT', '1h'),
]


def load_and_prepare_data(exchange: str, symbol: str, timeframe: str) -> pd.DataFrame | None:
    """데이터 로드 및 전처리"""
    try:
        dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})
        dm.load_historical()

        if dm.df_entry_full is None:
            print(f"  경고: {exchange} {symbol} 데이터 없음")
            return None

        df_15m = dm.df_entry_full.copy()

        # 1h로 리샘플링
        df_temp = df_15m.set_index('timestamp')
        df_1h = df_temp.resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        df_1h.reset_index(inplace=True)

        # 지표 추가
        add_all_indicators(df_1h, inplace=True)

        return df_1h

    except Exception as e:
        print(f"  에러: {exchange} {symbol} 로드 실패 - {e}")
        return None


def run_market_backtest(df: pd.DataFrame, params: dict) -> List[dict]:
    """시장가 백테스트 실행"""
    strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

    trades = strategy.run_backtest(
        df_pattern=df,
        df_entry=df,
        slippage=0.001,
        **params
    )

    return trades


def simulate_limit_orders(market_trades: List[dict], df: pd.DataFrame) -> List[dict]:
    """지정가 체결 시뮬레이션"""
    limit_trades = []

    for trade in market_trades:
        entry_idx = trade.get('entry_idx', 0)
        side = trade.get('type', 'Long')

        if entry_idx >= len(df):
            continue

        entry_candle = df.iloc[entry_idx]
        open_price = entry_candle['open']
        low = entry_candle['low']
        high = entry_candle['high']

        # 체결 여부 확인
        filled = False
        actual_entry = open_price

        if side == 'Long':
            limit_price = open_price * (1 - LIMIT_OFFSET)
            if low <= limit_price:
                filled = True
                actual_entry = limit_price
        else:  # Short
            limit_price = open_price * (1 + LIMIT_OFFSET)
            if high >= limit_price:
                filled = True
                actual_entry = limit_price

        if filled:
            adjusted_trade = trade.copy()
            original_entry = trade.get('entry_price', open_price)
            entry_diff_pct = (actual_entry - original_entry) / original_entry
            original_pnl = trade.get('pnl', 0)

            if side == 'Long':
                adjusted_pnl = original_pnl - (entry_diff_pct * 100)
            else:
                adjusted_pnl = original_pnl + (entry_diff_pct * 100)

            # 수수료 개선 반영
            adjusted_pnl += FEE_IMPROVEMENT
            adjusted_trade['pnl'] = adjusted_pnl
            adjusted_trade['entry_price'] = actual_entry
            limit_trades.append(adjusted_trade)

    return limit_trades


def calculate_metrics(trades: List[dict], leverage: int = 1) -> dict:
    """백테스트 메트릭 계산"""
    if not trades:
        return {
            'total_trades': 0,
            'fill_rate': 0.0,
            'win_rate': 0.0,
            'avg_pnl': 0.0,
            'total_pnl': 0.0,
            'compound_return': 0.0,
        }

    # 기본 통계
    total_trades = len(trades)
    wins = sum(1 for t in trades if t['pnl'] > 0)
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0

    # PnL 계산 (레버리지 적용)
    pnls = [t['pnl'] * leverage for t in trades]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
    total_pnl = sum(pnls)

    # 복리 수익률 계산 (오버플로우 방지)
    capital = 100.0
    for pnl in pnls:
        capital *= (1 + pnl / 100)
        if capital > 1e10:  # 오버플로우 방지
            capital = 1e10
            break
    compound_return = (capital - 100.0) / 100.0 * 100

    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_pnl': avg_pnl,
        'total_pnl': total_pnl,
        'compound_return': compound_return,
    }


def run_multi_symbol_backtest(symbols: List[tuple], params: dict, leverage: int = 5):
    """다중 심볼 백테스트 실행"""
    print("="*80)
    print("다중 심볼 백테스트 (지정가 주문 기준)")
    print("="*80 + "\n")

    print(f"설정:")
    print(f"  파라미터: atr_mult={params['atr_mult']}, filter_tf={params['filter_tf']}")
    print(f"  레버리지: {leverage}x")
    print(f"  지정가 오프셋: {LIMIT_OFFSET*100:.3f}%")
    print(f"  수수료 개선: {FEE_IMPROVEMENT}%\n")

    results = []

    for exchange, symbol, timeframe in symbols:
        print(f"\n{'='*80}")
        print(f"{exchange.upper()} {symbol} {timeframe}")
        print(f"{'='*80}\n")

        # 데이터 로드
        print("1단계: 데이터 로드 중...")
        df = load_and_prepare_data(exchange, symbol, timeframe)

        if df is None:
            print(f"  건너뛰기: 데이터 로드 실패\n")
            continue

        print(f"  OK: {len(df):,}개 캔들 로드 완료")

        # 시장가 백테스트
        print("\n2단계: 시장가 백테스트 실행 중...")
        market_trades = run_market_backtest(df, params)
        print(f"  OK: {len(market_trades):,}개 신호 생성")

        # 지정가 체결 시뮬레이션
        print("\n3단계: 지정가 체결 시뮬레이션 중...")
        limit_trades = simulate_limit_orders(market_trades, df)
        fill_rate = len(limit_trades) / len(market_trades) * 100 if market_trades else 0
        print(f"  OK: {len(limit_trades):,}개 체결 (체결률 {fill_rate:.1f}%)")

        # 메트릭 계산
        print("\n4단계: 성능 메트릭 계산 중...")
        metrics = calculate_metrics(limit_trades, leverage)

        results.append({
            'exchange': exchange,
            'symbol': symbol,
            'timeframe': timeframe,
            'market_trades': len(market_trades),
            'limit_trades': len(limit_trades),
            'fill_rate': fill_rate,
            **metrics
        })

        # 결과 출력
        print(f"\n결과:")
        print(f"  총 거래:       {metrics['total_trades']:,}회")
        print(f"  승률:          {metrics['win_rate']:.2f}%")
        print(f"  거래당 PnL:    {metrics['avg_pnl']:.3f}%")
        print(f"  총 PnL (단리): {metrics['total_pnl']:,.2f}%")
        print(f"  복리 수익률:   {metrics['compound_return']:,.2f}%")

    return results


def print_summary(results: List[dict]):
    """요약 리포트 출력"""
    if not results:
        print("\n경고: 백테스트 결과 없음")
        return

    print("\n" + "="*80)
    print("다중 심볼 백테스트 요약")
    print("="*80 + "\n")

    print(f"{'심볼':<15} {'거래수':>8} {'체결률':>8} {'승률':>8} {'거래당PnL':>12} {'총PnL':>12}")
    print("-"*80)

    for r in results:
        symbol_str = f"{r['exchange']}/{r['symbol']}"
        print(f"{symbol_str:<15} {r['limit_trades']:>8,} {r['fill_rate']:>7.1f}% {r['win_rate']:>7.2f}% {r['avg_pnl']:>11.3f}% {r['total_pnl']:>11,.0f}%")

    # 통합 통계
    total_trades = sum(r['limit_trades'] for r in results)
    avg_fill_rate = sum(r['fill_rate'] for r in results) / len(results)
    avg_win_rate = sum(r['win_rate'] for r in results) / len(results)
    avg_pnl = sum(r['avg_pnl'] for r in results) / len(results)
    total_pnl = sum(r['total_pnl'] for r in results)

    print("-"*80)
    print(f"{'평균/합계':<15} {total_trades:>8,} {avg_fill_rate:>7.1f}% {avg_win_rate:>7.2f}% {avg_pnl:>11.3f}% {total_pnl:>11,.0f}%")

    print("\n통합 지표:")
    print(f"  총 심볼 수:    {len(results)}개")
    print(f"  총 거래 수:    {total_trades:,}회")
    print(f"  평균 체결률:  {avg_fill_rate:.1f}%")
    print(f"  평균 승률:    {avg_win_rate:.2f}%")
    print(f"  평균 거래당:  {avg_pnl:.3f}%")
    print(f"  총 수익 (단리): {total_pnl:,.0f}%")

    print("\n심볼 분산 효과:")
    if total_trades > 0:
        avg_trades_per_symbol = total_trades / len(results)
        diversification_benefit = len(results) * avg_trades_per_symbol / total_trades
        print(f"  심볼당 평균 거래: {avg_trades_per_symbol:,.0f}회")
        print(f"  거래 빈도 증가:   {len(results):.1f}배 (심볼 수)")

        # 실제 거래 빈도 추정
        period_years = 5.8
        trades_per_day = total_trades / (period_years * 365)
        print(f"  일평균 거래 빈도: {trades_per_day:.2f}회/일 (전체 심볼)")
        print(f"  심볼당 거래 빈도: {trades_per_day/len(results):.2f}회/일")


if __name__ == "__main__":
    # 다중 심볼 백테스트 실행
    results = run_multi_symbol_backtest(
        symbols=TEST_SYMBOLS,
        params=BASELINE_PARAMS,
        leverage=5
    )

    # 요약 출력
    print_summary(results)

    print("\n" + "="*80)
    print("다음 단계 권장")
    print("="*80)
    print("\n1. 거래소 분산:")
    print("   - Binance, OKX, Bitget 등 추가")
    print("   - 거래소별 최소 2-3개 심볼")
    print("\n2. 심볼 선정 기준:")
    print("   - 승률 95% 이상")
    print("   - 체결률 90% 이상")
    print("   - 거래당 PnL 5% 이상 (5x 레버리지)")
    print("\n3. 자본 배분:")
    print("   - 심볼별 동일 비중 or 성능 비례")
    print("   - 총 자본 10억원 기준 심볼 수 결정")
    print("\n")
