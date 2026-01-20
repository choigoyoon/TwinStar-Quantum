"""v7.27 최적 결과를 프리셋으로 저장

CSV 1위 결과를 검증하고 프리셋 파일로 저장
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.preset_storage import PresetStorage
import pandas as pd

# CSV 파일 읽기
csv_path = "results/coarse_fine_results_20260120_004852.csv"
df = pd.read_csv(csv_path)

# 1위 결과 추출
best = df.iloc[0]

print("=" * 70)
print("v7.27 최적 결과 (CSV 1위)")
print("=" * 70)
print(f"\n핵심 지표:")
print(f"  Sharpe:   {best['sharpe']:.2f}")
print(f"  승률:     {best['win_rate']:.1f}%")
print(f"  MDD:      {best['mdd']:.2f}%")
print(f"  PnL:      {best['pnl']:.1f}%")
print(f"  거래:     {int(best['trades'])}회")
print(f"  PF:       {best['pf']:.2f}")
stability_str = str(best['stability']).replace('✅', 'A').replace('⚠', 'B').replace('❌', 'F')
print(f"  등급:     {stability_str}")

print(f"\n파라미터:")
params = {
    'atr_mult': best['atr_mult'],
    'filter_tf': best['filter_tf'],
    'entry_validity_hours': best['entry_validity_hours'],
    'trail_start_r': best['trail_start_r'],
    'trail_dist_r': best['trail_dist_r'],
    'leverage': int(best['leverage']),
    'macd_fast': int(best['macd_fast']),
    'macd_slow': int(best['macd_slow']),
    'macd_signal': int(best['macd_signal']),
    'tolerance': best.get('pattern_tolerance', 0.15),  # pattern_tolerance 사용
    'use_adx_filter': bool(best.get('enable_adx_filter', False))  # enable_adx_filter 사용
}

for k, v in params.items():
    print(f"  {k}: {v}")

# 프리셋 저장
storage = PresetStorage(base_path='presets')

optimization_result = {
    'sharpe_ratio': float(best['sharpe']),
    'win_rate': float(best['win_rate']),
    'mdd': float(best['mdd']),
    'total_pnl': float(best['pnl']),
    'total_trades': int(best['trades']),
    'profit_factor': float(best['pf']),
    'stability': str(best['stability']),
    'avg_pnl': float(best['avg_pnl']),
    'compound_return': float(best['compound_return'])
}

print("\n프리셋 저장 중...")
try:
    success = storage.save_preset(
        symbol='BTCUSDT',
        tf='1h',
        params=params,
        optimization_result=optimization_result,
        mode='coarse_to_fine',
        strategy_type='macd',
        exchange='bybit'
    )

    if success:
        print("\n[OK] 프리셋 저장 완료!")
        print(f"   경로: config/presets/auto/")
    else:
        print("\n[FAIL] 프리셋 저장 실패 (success=False)")
        sys.exit(1)
except Exception as e:
    print(f"\n[FAIL] 프리셋 저장 중 에러: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 저장된 프리셋 로드하여 검증
print("\n검증: 저장된 프리셋 로드")
loaded = storage.load_preset('BTCUSDT', '1h')

if loaded:
    print("[OK] 로드 성공")

    # 메트릭 비교
    opt = loaded['optimization']
    print("\n메트릭 비교:")
    print(f"  Sharpe:   {opt['sharpe_ratio']:.2f} (원본: {best['sharpe']:.2f})")
    print(f"  승률:     {opt['win_rate']:.1f}% (원본: {best['win_rate']:.1f}%)")
    print(f"  MDD:      {opt['mdd']:.2f}% (원본: {best['mdd']:.2f}%)")
    print(f"  거래:     {opt['total_trades']} (원본: {int(best['trades'])})")

    # 일치 확인
    sharpe_match = abs(opt['sharpe_ratio'] - best['sharpe']) < 0.01
    winrate_match = abs(opt['win_rate'] - best['win_rate']) < 0.01
    trades_match = opt['total_trades'] == int(best['trades'])

    if sharpe_match and winrate_match and trades_match:
        print("\n[OK] 검증 성공! 프리셋이 실제 백테스트 값과 일치합니다.")
    else:
        print("\n[FAIL] 검증 실패! 값이 일치하지 않습니다.")
        sys.exit(1)
else:
    print("[FAIL] 로드 실패")
    sys.exit(1)

print("\n" + "=" * 70)
print("완료!")
print("=" * 70)
