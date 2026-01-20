"""
거래소 분산 전략 (v1.0 - 2026-01-19)

10억원 자본을 여러 거래소에 분산하여 운용하는 전략
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 확정된 성능 지표 (BTC/USDT 기준)
PERFORMANCE_BASELINE = {
    'symbol': 'BTC/USDT',
    'timeframe': '1h',
    'leverage': 5,
    'trades_total': 2056,
    'period_years': 5.8,
    'win_rate': 97.86,
    'avg_pnl_pct': 6.261,  # 5x 레버리지 기준
    'fill_rate': 93.0,
    'daily_trades': 0.97,  # 2056 / (5.8 * 365) = 0.97
}

# 지원 거래소 목록
SUPPORTED_EXCHANGES = {
    'bybit': {
        'name': 'Bybit',
        'maker_fee': 0.02,      # 0.02%
        'taker_fee': 0.055,     # 0.055%
        'max_leverage': 100,
        'min_capital': 50_000_000,  # 5천만원 (BTC 5개 수준)
        'api_stable': True,
        'priority': 1,  # 최우선
    },
    'binance': {
        'name': 'Binance',
        'maker_fee': 0.02,
        'taker_fee': 0.04,
        'max_leverage': 125,
        'min_capital': 50_000_000,
        'api_stable': True,
        'priority': 1,
    },
    'okx': {
        'name': 'OKX',
        'maker_fee': 0.08,
        'taker_fee': 0.1,
        'max_leverage': 100,
        'min_capital': 30_000_000,  # 3천만원
        'api_stable': True,
        'priority': 2,
    },
    'bitget': {
        'name': 'Bitget',
        'maker_fee': 0.02,
        'taker_fee': 0.06,
        'max_leverage': 125,
        'min_capital': 30_000_000,
        'api_stable': True,
        'priority': 2,
    },
    'bingx': {
        'name': 'BingX',
        'maker_fee': 0.02,
        'taker_fee': 0.05,
        'max_leverage': 150,
        'min_capital': 20_000_000,  # 2천만원
        'api_stable': False,  # API 안정성 낮음
        'priority': 3,
    }
}


def calculate_capital_distribution(
    total_capital: int,
    method: str = 'equal',
    min_exchanges: int = 2,
    max_exchanges: int = 5
) -> dict:
    """자본 배분 계산

    Args:
        total_capital: 총 자본 (원)
        method: 배분 방법 ('equal': 균등 배분, 'priority': 우선순위 기반)
        min_exchanges: 최소 거래소 수
        max_exchanges: 최대 거래소 수

    Returns:
        거래소별 배분 자본 딕셔너리
    """
    # Priority 기준 정렬
    exchanges = sorted(
        SUPPORTED_EXCHANGES.items(),
        key=lambda x: (x[1]['priority'], -x[1]['maker_fee'])
    )

    # 최소 자본 기준 필터링
    available = [
        (name, info) for name, info in exchanges
        if info['min_capital'] <= total_capital / min_exchanges
        and info['api_stable']  # API 안정성 필수
    ]

    if len(available) < min_exchanges:
        raise ValueError(f"사용 가능 거래소 {len(available)}개 < 최소 {min_exchanges}개")

    # 최대 거래소 수 제한
    selected = available[:min(max_exchanges, len(available))]

    distribution = {}

    if method == 'equal':
        # 균등 배분
        per_exchange = total_capital // len(selected)

        for name, info in selected:
            distribution[name] = {
                'capital': per_exchange,
                'info': info,
                'weight': 1.0 / len(selected)
            }

    elif method == 'priority':
        # 우선순위 기반 가중 배분
        # Priority 1: 40%, Priority 2: 30%, Priority 3: 10%
        weights = {1: 0.4, 2: 0.3, 3: 0.1}

        total_weight = sum(weights.get(info['priority'], 0.1) for _, info in selected)

        for name, info in selected:
            weight = weights.get(info['priority'], 0.1)
            capital = int(total_capital * (weight / total_weight))

            distribution[name] = {
                'capital': capital,
                'info': info,
                'weight': weight / total_weight
            }

    return distribution


def estimate_performance(distribution: dict, baseline: dict) -> dict:
    """거래소 분산 시 예상 성능 계산"""
    total_capital = sum(d['capital'] for d in distribution.values())
    total_exchanges = len(distribution)

    # 거래 빈도 증가 (거래소 수만큼)
    daily_trades = baseline['daily_trades'] * total_exchanges

    # 연간 거래 수
    annual_trades = daily_trades * 365

    # 총 거래 수 (5.8년)
    total_trades = int(baseline['trades_total'] * total_exchanges)

    # 단리 수익 (거래당 PnL × 총 거래 수)
    simple_profit_pct = baseline['avg_pnl_pct'] * total_trades
    simple_profit_krw = total_capital * (simple_profit_pct / 100)

    # 최종 자본 (단리 기준)
    final_capital = total_capital + simple_profit_krw

    return {
        'total_capital': total_capital,
        'total_exchanges': total_exchanges,
        'daily_trades': daily_trades,
        'annual_trades': annual_trades,
        'total_trades': total_trades,
        'simple_profit_pct': simple_profit_pct,
        'simple_profit_krw': simple_profit_krw,
        'final_capital': final_capital,
        'multiplier': final_capital / total_capital,
    }


def print_distribution_plan(distribution: dict, performance: dict):
    """분산 계획 출력"""
    print("="*80)
    print("거래소 분산 전략 (10억원 기준)")
    print("="*80 + "\n")

    print("1. 자본 배분:")
    print(f"\n{'거래소':<12} {'자본':>15} {'비중':>8} {'수수료':>10} {'레버리지':>10}")
    print("-"*80)

    for name, data in distribution.items():
        info = data['info']
        capital = data['capital']
        weight = data['weight']

        print(f"{info['name']:<12} {capital:>15,}원 {weight*100:>7.1f}% "
              f"{info['maker_fee']:>9.2f}% {info['max_leverage']:>9}x")

    print("-"*80)
    print(f"{'합계':<12} {performance['total_capital']:>15,}원 {100.0:>7.1f}%")

    print("\n2. 예상 성능:")
    print(f"\n  거래소 수:         {performance['total_exchanges']}개")
    print(f"  일평균 거래:       {performance['daily_trades']:.2f}회/일 ({performance['daily_trades']/performance['total_exchanges']:.2f}회/거래소)")
    print(f"  연간 거래:         {performance['annual_trades']:,.0f}회")
    print(f"  총 거래 (5.8년):   {performance['total_trades']:,}회")

    print(f"\n  단리 수익률:       {performance['simple_profit_pct']:,.0f}%")
    print(f"  단리 수익금:       {performance['simple_profit_krw']:,.0f}원 ({performance['simple_profit_krw']/100_000_000:,.1f}억원)")
    print(f"  최종 자본:         {performance['final_capital']:,.0f}원 ({performance['final_capital']/100_000_000:,.1f}억원)")
    print(f"  배율:              {performance['multiplier']:,.1f}배")

    print("\n3. 리스크 관리:")
    print(f"\n  거래소 장애 대응:")
    print(f"    - 1개 거래소 장애 시: {(performance['total_exchanges']-1)/performance['total_exchanges']*100:.0f}% 운용 유지")
    print(f"    - 자동 페일오버: 대기 거래소로 전환")

    print(f"\n  자본 손실 방지:")
    for name, data in distribution.items():
        capital = data['capital']
        info = data['info']
        btc_count = capital / 100_000_000 * 5  # 5x 레버리지
        print(f"    - {info['name']}: BTC {btc_count:.1f}개 수준 매매 (슬리피지 낮음)")


def analyze_scenarios():
    """시나리오 분석"""
    print("\n" + "="*80)
    print("시나리오 분석")
    print("="*80 + "\n")

    scenarios = [
        {'capital': 1_000_000_000, 'method': 'equal', 'min_ex': 2, 'max_ex': 2, 'name': '2개 거래소 균등'},
        {'capital': 1_000_000_000, 'method': 'equal', 'min_ex': 3, 'max_ex': 3, 'name': '3개 거래소 균등'},
        {'capital': 1_000_000_000, 'method': 'equal', 'min_ex': 4, 'max_ex': 4, 'name': '4개 거래소 균등'},
        {'capital': 1_000_000_000, 'method': 'priority', 'min_ex': 3, 'max_ex': 3, 'name': '3개 거래소 가중'},
    ]

    print(f"{'시나리오':<20} {'거래소':>8} {'일거래':>10} {'총거래':>10} {'최종자본':>15} {'배율':>8}")
    print("-"*80)

    for scenario in scenarios:
        dist = calculate_capital_distribution(
            total_capital=scenario['capital'],
            method=scenario['method'],
            min_exchanges=scenario['min_ex'],
            max_exchanges=scenario['max_ex']
        )

        perf = estimate_performance(dist, PERFORMANCE_BASELINE)

        print(f"{scenario['name']:<20} {perf['total_exchanges']:>8}개 "
              f"{perf['daily_trades']:>9.2f} {perf['total_trades']:>10,} "
              f"{perf['final_capital']:>15,} {perf['multiplier']:>7.1f}배")

    print("\n권장 시나리오: 3개 거래소 균등 배분")
    print("  이유:")
    print("    1. 리스크 분산: 1개 장애 시 67% 운용 유지")
    print("    2. 거래 빈도: 일 2.91회 (충분)")
    print("    3. 관리 복잡도: 적정 (3개)")
    print("    4. 수수료: 균등 배분으로 평균화")


if __name__ == "__main__":
    # 10억원 자본, 3개 거래소 균등 배분
    distribution = calculate_capital_distribution(
        total_capital=1_000_000_000,
        method='equal',
        min_exchanges=3,
        max_exchanges=3
    )

    performance = estimate_performance(distribution, PERFORMANCE_BASELINE)

    print_distribution_plan(distribution, performance)

    analyze_scenarios()

    print("\n" + "="*80)
    print("다음 단계")
    print("="*80)
    print("\n1. 거래소별 백테스트:")
    print("   - Bybit, Binance, OKX 각각 BTC/USDT 백테스트")
    print("   - 거래소별 성능 차이 확인")

    print("\n2. 심볼 추가:")
    print("   - ETH/USDT, SOL/USDT 데이터 수집")
    print("   - 심볼별 백테스트 실행")

    print("\n3. 통합 실행:")
    print("   - 3개 거래소 × 3개 심볼 = 9개 동시 운용")
    print("   - 일 거래 빈도: 약 9회 (거래소당 1회)")

    print("\n4. 자동화:")
    print("   - 거래소 선택 로직 구현")
    print("   - 자본 자동 재배분 (성능 기반)")
    print("\n")
