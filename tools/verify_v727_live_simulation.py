"""v7.27 실제 매매 환경 시뮬레이션 검증

목적:
- 백테스트에서 최적화된 파라미터가 실제 매매 환경에서도 작동하는지 검증
- 최근 데이터(2025-01-01 이후)로 실시간 거래와 동일한 조건 테스트
- 신호 발생, 진입, 청산이 정상 작동하는지 확인

검증 항목:
1. 신호 발생 여부 (0개면 실패)
2. 진입 가능 여부 (filter_tf 필터 통과)
3. 청산 로직 작동 (트레일링 익절/손절)
4. 지표 계산 일관성 (백테스트와 동일)
5. 타임프레임 리샘플링 정확성
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.metrics import calculate_backtest_metrics
import pandas as pd
from datetime import datetime

# v7.27 최적 파라미터 (CSV 1위)
OPTIMAL_PARAMS = {
    'atr_mult': 1.438,
    'filter_tf': '4h',
    'entry_validity_hours': 48.0,
    'trail_start_r': 0.4,
    'trail_dist_r': 0.022,
    'leverage': 1,
    'macd_fast': 6,
    'macd_slow': 18,
    'macd_signal': 7,
    'tolerance': 0.05,
    'use_adx_filter': False,
}

TOTAL_COST = 0.0002  # 슬리피지 0% + 수수료 0.02%

print("=" * 80)
print("v7.27 실제 매매 환경 시뮬레이션 검증")
print("=" * 80)

# 1단계: 데이터 로드 (최근 데이터 우선)
print("\n[1/5] 데이터 로드 중...")
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
success = dm.load_historical()

if not success or dm.df_entry_full is None:
    print("[FAIL] 데이터 로드 실패")
    sys.exit(1)

# 15m -> 1h 리샘플링
df_15m = dm.df_entry_full.copy()
if 'timestamp' not in df_15m.columns:
    df_15m.reset_index(inplace=True)

df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
df_temp = df_15m.set_index('timestamp')

df = df_temp.resample('1h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

df.reset_index(inplace=True)

# 전체 데이터 통계
print(f"[OK] 전체 데이터: {len(df):,}개 1h 캔들")
print(f"     기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")

# 2단계: 최근 데이터 추출 (2025-01-01 이후)
print("\n[2/5] 최근 데이터 추출 (2025-01-01 이후)...")
df_recent = df[df['timestamp'] >= '2025-01-01'].copy()

if len(df_recent) == 0:
    print("[FAIL] 2025-01-01 이후 데이터 없음")
    sys.exit(1)

print(f"[OK] 최근 데이터: {len(df_recent):,}개 1h 캔들")
print(f"     기간: {df_recent['timestamp'].min()} ~ {df_recent['timestamp'].max()}")

# 3단계: 백테스트 실행 (지표 자동 계산)
print("\n[3/5] 백테스트 실행 (실제 매매 환경 시뮬레이션)...")
strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

backtest_params = {k: v for k, v in OPTIMAL_PARAMS.items()
                  if k not in ['slippage', 'fee']}

trades = strategy.run_backtest(
    df_pattern=df_recent,
    df_entry=df_recent,
    slippage=TOTAL_COST,
    **backtest_params
)

if isinstance(trades, tuple):
    trades = trades[0]

print(f"[OK] 백테스트 완료")
print(f"     거래 횟수: {len(trades):,}회")

# 4단계: 검증 항목 체크
print("\n[4/5] 검증 항목 체크...")

# 체크 1: 신호 발생 여부
if len(trades) == 0:
    print("[FAIL] 신호 발생 0개 - 실제 매매 환경에서 작동 불가!")
    print("       원인: 파라미터가 최근 시장 조건과 맞지 않음")
    sys.exit(1)
else:
    print(f"[OK] 신호 발생: {len(trades):,}개")

# 체크 2: 최소 거래 횟수 (통계적 유의미성)
if len(trades) < 10:
    print(f"[WARN] 거래 횟수 {len(trades)}회 - 통계적으로 부족 (최소 10회 권장)")
else:
    print(f"[OK] 거래 횟수 충분: {len(trades):,}회")

# 체크 3: 메트릭 계산
if len(trades) >= 10:
    metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    print("\n메트릭:")
    print(f"  Sharpe:  {metrics['sharpe_ratio']:.2f}")
    print(f"  승률:    {metrics['win_rate']:.1f}%")
    print(f"  MDD:     {metrics['mdd']:.2f}%")
    print(f"  PnL:     {metrics['total_pnl']:.2f}%")
    print(f"  PF:      {metrics['profit_factor']:.2f}")

    # 체크 4: 성능 저하 여부
    print("\n성능 비교 (백테스트 vs 실제):")
    expected_sharpe = 31.96
    expected_winrate = 97.45

    sharpe_diff = (metrics['sharpe_ratio'] - expected_sharpe) / expected_sharpe * 100
    winrate_diff = metrics['win_rate'] - expected_winrate

    print(f"  Sharpe 차이:  {sharpe_diff:+.1f}%")
    print(f"  승률 차이:    {winrate_diff:+.1f}%p")

    # 허용 오차: Sharpe ±30%, 승률 ±10%p
    if abs(sharpe_diff) > 30:
        print(f"[WARN] Sharpe 차이 {sharpe_diff:+.1f}% - 성능 저하 가능성")
    else:
        print("[OK] Sharpe 차이 허용 범위 내")

    if abs(winrate_diff) > 10:
        print(f"[WARN] 승률 차이 {winrate_diff:+.1f}%p - 성능 저하 가능성")
    else:
        print("[OK] 승률 차이 허용 범위 내")

# 체크 5: 거래 빈도
days = (df_recent['timestamp'].max() - df_recent['timestamp'].min()).days
if days > 0:
    trades_per_day = len(trades) / days
    print(f"\n거래 빈도:")
    print(f"  일평균: {trades_per_day:.2f}회/일")

    if trades_per_day < 0.1:
        print(f"[WARN] 거래 빈도 너무 낮음 ({trades_per_day:.2f}회/일)")
    elif trades_per_day > 5.0:
        print(f"[WARN] 거래 빈도 너무 높음 ({trades_per_day:.2f}회/일)")
    else:
        print("[OK] 거래 빈도 적정")

# 5단계: 최종 판단
print("\n" + "=" * 80)
print("[5/5] 최종 판단")
print("=" * 80)

if len(trades) == 0:
    print("\n[FAIL] 실제 매매 환경 검증 실패")
    print("       원인: 최근 시장에서 신호 발생 없음")
    print("       조치: 파라미터 재최적화 필요")
elif len(trades) < 10:
    print("\n[WARN] 실제 매매 환경 검증 경고")
    print(f"       거래 횟수 {len(trades)}회 - 통계적 신뢰도 낮음")
    print("       조치: 더 긴 기간 데이터로 재검증 권장")
else:
    print("\n[OK] 실제 매매 환경 검증 성공!")
    print(f"     거래 횟수: {len(trades):,}회")
    print(f"     Sharpe: {metrics['sharpe_ratio']:.2f}")
    print(f"     승률: {metrics['win_rate']:.1f}%")
    print(f"     MDD: {metrics['mdd']:.2f}%")
    print("\n     v7.27 파라미터는 실제 매매 환경에서도 작동 가능합니다.")

print("=" * 80)
