"""v7.27 최적 결과를 프리셋으로 저장 (간단 버전)

CSV 1위 결과를 JSON으로 직접 저장
"""
import sys
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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

# 프리셋 데이터 생성
preset_data = {
    'meta_info': {
        'exchange': 'bybit',
        'symbol': 'BTCUSDT',
        'timeframe': '1h',
        'strategy_type': 'macd',
        'optimization_method': 'coarse_to_fine',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': 'v7.27'
    },
    'best_params': {
        'atr_mult': float(best['atr_mult']),
        'filter_tf': str(best['filter_tf']),
        'entry_validity_hours': float(best['entry_validity_hours']),
        'trail_start_r': float(best['trail_start_r']),
        'trail_dist_r': float(best['trail_dist_r']),
        'leverage': int(best['leverage']),
        'macd_fast': int(best['macd_fast']),
        'macd_slow': int(best['macd_slow']),
        'macd_signal': int(best['macd_signal']),
        'tolerance': float(best.get('pattern_tolerance', 0.05)),
        'use_adx_filter': bool(best.get('enable_adx_filter', False))
    },
    'best_metrics': {
        'sharpe_ratio': float(best['sharpe']),
        'win_rate': float(best['win_rate']),
        'mdd': float(best['mdd']),
        'total_pnl': float(best['pnl']),
        'total_trades': int(best['trades']),
        'profit_factor': float(best['pf']),
        'stability': stability_str,
        'avg_pnl': float(best['avg_pnl']),
        'compound_return': float(best['compound_return'])
    }
}

# 저장 경로
preset_dir = project_root / 'presets'
preset_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f'bybit_BTCUSDT_1h_macd_v727_{timestamp}.json'
filepath = preset_dir / filename

# JSON 저장
print(f"\n프리셋 저장 중...")
print(f"   경로: {filepath}")

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(preset_data, f, indent=2, ensure_ascii=False)

print("\n[OK] 프리셋 저장 완료!")

# 검증: 저장된 파일 다시 읽기
with open(filepath, 'r', encoding='utf-8') as f:
    loaded = json.load(f)

print("\n검증: 저장된 프리셋 로드")
opt = loaded['best_metrics']
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
    print(f"\n프리셋 파일: {filename}")
else:
    print("\n[FAIL] 검증 실패! 값이 일치하지 않습니다.")
    sys.exit(1)
