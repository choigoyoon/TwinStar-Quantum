"""지정가 주문 체결률 테스트

신호 발생 후 다음 봉에서 지정가 주문이 체결될 확률을 계산합니다.

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

import sys
import pandas as pd
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def test_limit_order_fill_rate(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    timeframe: str = '1h',
    slippage_percent: float = 0.1
):
    """지정가 주문 체결률 테스트

    Args:
        exchange: 거래소명
        symbol: 심볼명
        timeframe: 타임프레임
        slippage_percent: 허용 슬리피지 (%, 기본 0.1%)

    Returns:
        dict: 체결률 통계
    """
    logger.info("=" * 80)
    logger.info(f"지정가 주문 체결률 테스트 시작")
    logger.info(f"거래소: {exchange}, 심볼: {symbol}, TF: {timeframe}")
    logger.info(f"허용 슬리피지: {slippage_percent}%")
    logger.info("=" * 80)

    # 1. 데이터 로드
    logger.info("\n[1/4] 데이터 로드 중...")
    dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})

    if not dm.load_historical():
        logger.error("데이터 로드 실패")
        return None

    df = dm.get_full_history()
    if df is None or len(df) == 0:
        logger.error("데이터 없음")
        return None
    logger.info(f"  OK {len(df):,}개 캔들 로드")

    # 2. 프리셋 파라미터 로드 (MACD 기준)
    logger.info("\n[2/4] 프리셋 파라미터 사용...")
    params = {
        'macd_fast': 6,
        'macd_slow': 18,
        'macd_signal': 7,
        'atr_mult': 1.5,
        'filter_tf': '4h',
        'trail_start_r': 1.2,
        'trail_dist_r': 0.03,
        'entry_validity_hours': 6.0,
        'tolerance': 0.05,
        'enable_adx_filter': False,
    }
    logger.info(f"  OK MACD preset (filter_tf={params['filter_tf']}, atr_mult={params['atr_mult']})")

    # 3. 지표 추가
    logger.info("\n[3/5] 지표 계산 중...")
    from utils.indicators import add_all_indicators
    df_copy = df.copy()
    add_all_indicators(df_copy, inplace=True)  # inplace=True이므로 df_copy 수정됨
    logger.info(f"  OK 지표 완료")

    # 4. 백테스트 실행 (신호만 추출)
    logger.info("\n[4/5] 백테스트 실행 (신호 추출)...")
    strategy = AlphaX7Core()
    backtest_result = strategy.run_backtest(
        df_pattern=df_copy,
        df_entry=df_copy,
        **params  # params dict를 키워드 인자로 풀기
    )

    logger.info(f"  DEBUG: backtest_result type = {type(backtest_result)}")
    logger.info(f"  DEBUG: backtest_result keys = {list(backtest_result.keys()) if isinstance(backtest_result, dict) else 'not dict'}")

    if not backtest_result or 'trades' not in backtest_result:
        logger.error("백테스트 실패 또는 거래 없음")
        if backtest_result:
            logger.error(f"  Result: {backtest_result}")
        return None

    trades = backtest_result['trades']
    logger.info(f"  OK {len(trades)}건 거래 발견")

    # 5. 지정가 체결률 계산
    logger.info(f"\n[5/5] 지정가 체결률 계산 (슬리피지 ±{slippage_percent}%)...")

    slippage_multiplier = slippage_percent / 100.0  # 0.1% → 0.001

    stats = {
        'total_signals': len(trades),
        'long_signals': 0,
        'short_signals': 0,
        'long_filled': 0,
        'short_filled': 0,
        'long_failed': 0,
        'short_failed': 0,
        'long_fill_rate': 0.0,
        'short_fill_rate': 0.0,
        'overall_fill_rate': 0.0,
    }

    for trade in trades:
        entry_idx = trade.get('entry_idx')
        side = trade.get('side', 'Long')
        entry_price = trade.get('entry_price')

        if entry_idx is None or entry_idx >= len(df) - 1:
            continue

        # 다음 봉 정보
        next_candle = df.iloc[entry_idx + 1]
        next_open = next_candle['open']
        next_high = next_candle['high']
        next_low = next_candle['low']

        # 진입 시도 (신호 발생 후 다음 봉 open)
        # 실제 entry_price는 백테스트에서 next_open 기준으로 계산됨

        if side == 'Long':
            stats['long_signals'] += 1

            # Long 지정가 = open × (1 + slippage)
            # 다음 봉에서 Low ≤ 지정가 이면 체결 가능
            limit_price = next_open * (1 + slippage_multiplier)

            if next_low <= limit_price:
                stats['long_filled'] += 1
            else:
                stats['long_failed'] += 1

        elif side == 'Short':
            stats['short_signals'] += 1

            # Short 지정가 = open × (1 - slippage)
            # 다음 봉에서 High ≥ 지정가 이면 체결 가능
            limit_price = next_open * (1 - slippage_multiplier)

            if next_high >= limit_price:
                stats['short_filled'] += 1
            else:
                stats['short_failed'] += 1

    # 체결률 계산
    if stats['long_signals'] > 0:
        stats['long_fill_rate'] = (stats['long_filled'] / stats['long_signals']) * 100

    if stats['short_signals'] > 0:
        stats['short_fill_rate'] = (stats['short_filled'] / stats['short_signals']) * 100

    if stats['total_signals'] > 0:
        total_filled = stats['long_filled'] + stats['short_filled']
        stats['overall_fill_rate'] = (total_filled / stats['total_signals']) * 100

    # 5. 결과 출력
    logger.info("\n" + "=" * 80)
    logger.info("📊 지정가 주문 체결률 분석 결과")
    logger.info("=" * 80)

    logger.info(f"\n전체 신호: {stats['total_signals']:,}개")
    logger.info(f"  - Long: {stats['long_signals']:,}개")
    logger.info(f"  - Short: {stats['short_signals']:,}개")

    logger.info(f"\n체결 성공:")
    logger.info(f"  - Long: {stats['long_filled']:,}개 ({stats['long_fill_rate']:.2f}%)")
    logger.info(f"  - Short: {stats['short_filled']:,}개 ({stats['short_fill_rate']:.2f}%)")
    logger.info(f"  - 전체: {stats['long_filled'] + stats['short_filled']:,}개 ({stats['overall_fill_rate']:.2f}%)")

    logger.info(f"\n체결 실패:")
    logger.info(f"  - Long: {stats['long_failed']:,}개 ({100 - stats['long_fill_rate']:.2f}%)")
    logger.info(f"  - Short: {stats['short_failed']:,}개 ({100 - stats['short_fill_rate']:.2f}%)")
    logger.info(f"  - 전체: {stats['long_failed'] + stats['short_failed']:,}개 ({100 - stats['overall_fill_rate']:.2f}%)")

    logger.info("\n" + "=" * 80)
    logger.info("💡 분석:")
    logger.info("=" * 80)

    if stats['overall_fill_rate'] >= 95:
        logger.info(f"✅ 체결률 {stats['overall_fill_rate']:.1f}% - 지정가 주문 사용 가능!")
        logger.info(f"   슬리피지 {slippage_percent}% 범위 내에서 대부분 체결 가능합니다.")
    elif stats['overall_fill_rate'] >= 85:
        logger.info(f"⚠️  체결률 {stats['overall_fill_rate']:.1f}% - 일부 기회 손실 가능")
        logger.info(f"   슬리피지를 {slippage_percent * 1.5:.2f}%로 늘리면 개선될 수 있습니다.")
    else:
        logger.info(f"❌ 체결률 {stats['overall_fill_rate']:.1f}% - 지정가 주문 부적합")
        logger.info(f"   슬리피지 {slippage_percent}%로는 많은 기회를 놓칩니다.")
        logger.info(f"   시장가 주문 또는 더 큰 슬리피지 필요.")

    # 수수료 절감 효과
    logger.info("\n" + "=" * 80)
    logger.info("💰 수수료 절감 효과 (지정가 = Maker)")
    logger.info("=" * 80)

    market_fee = 0.055  # 시장가 (Taker)
    limit_fee = 0.02    # 지정가 (Maker)
    fee_saved_per_trade = market_fee - limit_fee  # 0.035%

    filled_trades = stats['long_filled'] + stats['short_filled']
    total_fee_saved = filled_trades * fee_saved_per_trade

    logger.info(f"시장가 수수료: {market_fee}% (Taker)")
    logger.info(f"지정가 수수료: {limit_fee}% (Maker)")
    logger.info(f"거래당 절감: {fee_saved_per_trade}%")
    logger.info(f"\n체결 성공 거래: {filled_trades:,}개")
    logger.info(f"총 수수료 절감: {total_fee_saved:.2f}% (누적)")
    logger.info(f"거래당 평균: +{fee_saved_per_trade:.3f}% 추가 수익")

    logger.info("\n" + "=" * 80)

    return stats


if __name__ == '__main__':
    # 기본 테스트: 0.1% 슬리피지
    print("\n" + "=" * 80)
    print("TEST 1: Slippage 0.1%")
    print("=" * 80)
    result_01 = test_limit_order_fill_rate(slippage_percent=0.1)

    # 추가 테스트: 0.2% 슬리피지
    print("\n\n" + "=" * 80)
    print("TEST 2: Slippage 0.2%")
    print("=" * 80)
    result_02 = test_limit_order_fill_rate(slippage_percent=0.2)

    # 비교
    if result_01 and result_02:
        print("\n\n" + "=" * 80)
        print("COMPARISON: 0.1% vs 0.2%")
        print("=" * 80)
        print(f"Fill Rate 0.1%: {result_01['overall_fill_rate']:.2f}%")
        print(f"Fill Rate 0.2%: {result_02['overall_fill_rate']:.2f}%")
        print(f"Difference: +{result_02['overall_fill_rate'] - result_01['overall_fill_rate']:.2f}%p")

        extra_fills = (result_02['long_filled'] + result_02['short_filled']) - \
                      (result_01['long_filled'] + result_01['short_filled'])
        print(f"\nExtra fills with 0.2%: {extra_fills} trades")
        print("=" * 80)
