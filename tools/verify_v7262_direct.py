"""v7.26.2 최적 파라미터 직접 백테스트

프리셋 없이 v7.26.2 파라미터로 BTC 15분 데이터 백테스트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.metrics import calculate_backtest_metrics
import pandas as pd

def main():
    print("=" * 100)
    print("v7.26.2 최적 파라미터 직접 백테스트")
    print("=" * 100)

    # v7.26.2 최적 파라미터 (사용자 제공 결과)
    optimal_params = {
        'atr_mult': 1.438,
        'filter_tf': '4h',
        'entry_validity_hours': 48,
        'trail_start_r': 0.37,
        'trail_dist_r': 0.038,
        'leverage': 1,

        # 전략 파라미터
        'macd_fast': 6,
        'macd_slow': 18,
        'macd_signal': 7,
        'tolerance': 0.15,
        'use_adx_filter': False,
    }

    print("\n최적 파라미터:")
    for key, val in optimal_params.items():
        print(f"  {key}: {val}")

    # 1. 데이터 로드
    print("\n" + "=" * 100)
    print("1단계: 데이터 로드 및 리샘플링")
    print("=" * 100)

    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    success = dm.load_historical()

    if not success or dm.df_entry_full is None:
        print("❌ 데이터 로드 실패")
        sys.exit(1)

    # 15m → 1h 리샘플링
    df_15m = dm.df_entry_full.copy()

    if 'timestamp' not in df_15m.columns:
        df_15m.reset_index(inplace=True)

    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_temp = df_15m.set_index('timestamp')

    df_1h = df_temp.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    df_1h.reset_index(inplace=True)

    # 2020년 이후 필터링
    df_1h = df_1h[df_1h['timestamp'] >= '2020-01-01'].copy()

    start_date = df_1h['timestamp'].iloc[0]
    end_date = df_1h['timestamp'].iloc[-1]
    total_days = (end_date - start_date).days
    total_hours = len(df_1h)

    print(f"\n[OK] 데이터 로드 완료:")
    print(f"  15m 캔들: {len(df_15m):,}개")
    print(f"  1h 캔들: {len(df_1h):,}개 (2020년 이후)")
    print(f"  시작: {start_date}")
    print(f"  종료: {end_date}")
    print(f"  기간: {total_days:,}일 ({total_hours:,}시간)")

    # 2. 지표 추가 (SKIP - run_backtest가 자동으로 계산함)
    print("\n" + "=" * 100)
    print("2단계: 지표 계산 (SKIP - AlphaX7Core가 자동 처리)")
    print("=" * 100)

    # 지표를 미리 계산하면 run_backtest 내부에서 중복 계산되어 문제 발생!
    # add_all_indicators(df_1h, inplace=True)  # ← 제거
    print("[OK] 백테스트 시 자동 계산됨")

    # 3. 백테스트 실행
    print("\n" + "=" * 100)
    print("3단계: 백테스트 실행")
    print("=" * 100)

    strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

    # slippage/fee 제외한 파라미터
    backtest_params = {k: v for k, v in optimal_params.items()
                      if k not in ['slippage', 'fee']}

    trades = strategy.run_backtest(
        df_pattern=df_1h,
        df_entry=df_1h,
        slippage=0.0,  # v7.26.2는 지정가 주문 (슬리피지 0%)
        **backtest_params
    )

    if not trades:
        print("[FAIL] 백테스트 실패 (거래 없음)")
        sys.exit(1)

    print(f"[OK] 백테스트 완료: {len(trades):,}회 거래")

    # 4. 메트릭 계산
    print("\n" + "=" * 100)
    print("4단계: 메트릭 계산")
    print("=" * 100)

    metrics = calculate_backtest_metrics(
        trades=trades,
        leverage=optimal_params.get('leverage', 1),
        capital=100.0
    )

    print("[OK] 메트릭 계산 완료")

    # 5. 결과 출력
    print("\n" + "=" * 100)
    print("백테스트 결과")
    print("=" * 100)

    print(f"\n📊 핵심 지표:")
    print(f"  Sharpe Ratio:   {metrics['sharpe_ratio']:.2f}")
    print(f"  승률:           {metrics['win_rate']:.1f}%")
    print(f"  MDD:            {metrics['mdd']:.2f}%")
    print(f"  Profit Factor:  {metrics['profit_factor']:.2f}")

    print(f"\n💰 수익 지표:")
    print(f"  단리 수익:      {metrics['total_pnl']:.2f}%")
    print(f"  복리 수익:      {metrics['compound_return']:.2f}%")
    print(f"  거래당 평균:    {metrics['avg_pnl']:.2f}%")

    print(f"\n📈 거래 통계:")
    print(f"  총 거래:        {metrics['total_trades']:,}회")
    print(f"  승리:           {metrics['winning_trades']:,}회")
    print(f"  손실:           {metrics['losing_trades']:,}회")

    # 6. 거래 빈도 분석
    print(f"\n⏱️ 거래 빈도 분석:")
    trades_per_day = metrics['total_trades'] / total_days
    print(f"  일평균:         {trades_per_day:.2f}회/일")
    print(f"  건당 PnL:       {metrics['avg_pnl']:.2f}%")

    daily_gross = trades_per_day * metrics['avg_pnl']
    daily_cost = trades_per_day * 0.02  # 수수료만 (슬리피지 0%)
    daily_net = daily_gross - daily_cost

    print(f"\n일일 수익 분석:")
    print(f"  총 수익:        {daily_gross:.2f}%/일")
    print(f"  거래 비용:      {daily_cost:.2f}%/일 (수수료 0.02%)")
    print(f"  순 수익:        {daily_net:.2f}%/일")

    # 7. 안전성
    print(f"\n🎯 안전성:")
    safe_lev = 10.0 / metrics['mdd'] if metrics['mdd'] > 0 else 1.0
    safe_lev = min(safe_lev, 20.0)
    print(f"  안전 레버리지:  {safe_lev:.1f}x")

    # 8. v7.26.2 비교
    print("\n" + "=" * 100)
    print("v7.26.2 Coarse-to-Fine 결과와 비교")
    print("=" * 100)

    v7262 = {
        'sharpe': 21.42,
        'win_rate': 89.5,
        'mdd': 2.9,
        'pnl': 3643.8,
        'trades': 9058,
        'pf': 16.35,
    }

    print(f"\n{'지표':<20} {'Coarse-to-Fine':>18} {'직접 백테스트':>18} {'차이':>12}")
    print("=" * 70)
    print(f"{'Sharpe Ratio':<20} {v7262['sharpe']:>18.2f} {metrics['sharpe_ratio']:>18.2f} {metrics['sharpe_ratio'] - v7262['sharpe']:>12.2f}")
    print(f"{'승률 (%)':<20} {v7262['win_rate']:>18.1f} {metrics['win_rate']:>18.1f} {metrics['win_rate'] - v7262['win_rate']:>12.1f}")
    print(f"{'MDD (%)':<20} {v7262['mdd']:>18.2f} {metrics['mdd']:>18.2f} {metrics['mdd'] - v7262['mdd']:>12.2f}")
    print(f"{'PnL (%)':<20} {v7262['pnl']:>18.1f} {metrics['total_pnl']:>18.1f} {metrics['total_pnl'] - v7262['pnl']:>12.1f}")
    print(f"{'거래 횟수':<20} {v7262['trades']:>18,} {metrics['total_trades']:>18,} {metrics['total_trades'] - v7262['trades']:>12,}")
    print(f"{'Profit Factor':<20} {v7262['pf']:>18.2f} {metrics['profit_factor']:>18.2f} {metrics['profit_factor'] - v7262['pf']:>12.2f}")

    # 9. 복리 효과
    print("\n" + "=" * 100)
    print("복리 효과 계산")
    print("=" * 100)

    daily_return = daily_net / 100
    monthly_compound = (1 + daily_return) ** 30 - 1
    yearly_compound = (1 + daily_return) ** 365 - 1

    print(f"\n일 순수익:  {daily_net:.2f}% ({trades_per_day:.2f}회 × {metrics['avg_pnl']:.2f}% - {daily_cost:.2f}%)")
    print(f"30일 복리:  {monthly_compound * 100:.2f}%")
    print(f"연간 복리:  {yearly_compound * 100:.2f}%")

    print("\n" + "=" * 100)
    print("검증 완료")
    print("=" * 100)

if __name__ == '__main__':
    main()
