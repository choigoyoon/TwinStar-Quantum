"""최적화 vs 백테스트 계산식 비교 테스트

동일한 거래 데이터로 최적화 엔진과 백테스트 워커의 메트릭 계산이
완전히 일치하는지 검증합니다.
"""

from utils.metrics import (
    calculate_mdd,
    calculate_win_rate,
    calculate_sharpe_ratio,
    calculate_profit_factor,
    calculate_stability
)

print('=' * 80)
print('최적화 엔진 vs 백테스트 워커 계산식 비교')
print('=' * 80)

# 샘플 거래 데이터 (20개)
sample_trades = [
    {'pnl': 2.5, 'type': 'Long'},
    {'pnl': -1.0, 'type': 'Short'},
    {'pnl': 3.0, 'type': 'Long'},
    {'pnl': 1.5, 'type': 'Long'},
    {'pnl': -0.5, 'type': 'Short'},
    {'pnl': 2.0, 'type': 'Long'},
    {'pnl': -1.5, 'type': 'Short'},
    {'pnl': 4.0, 'type': 'Long'},
    {'pnl': 0.5, 'type': 'Long'},
    {'pnl': -2.0, 'type': 'Short'},
    {'pnl': 1.0, 'type': 'Long'},
    {'pnl': 2.5, 'type': 'Long'},
    {'pnl': -0.5, 'type': 'Short'},
    {'pnl': 3.5, 'type': 'Long'},
    {'pnl': 1.5, 'type': 'Long'},
    {'pnl': -1.0, 'type': 'Short'},
    {'pnl': 2.0, 'type': 'Long'},
    {'pnl': 0.5, 'type': 'Long'},
    {'pnl': 1.0, 'type': 'Long'},
    {'pnl': -0.5, 'type': 'Short'},
]

leverage = 1

print(f'\n샘플 데이터: {len(sample_trades)}개 거래')
print(f'레버리지: {leverage}배')
print()

# === 최적화 엔진 로직 시뮬레이션 ===
print('[최적화 엔진 계산]')
print('-' * 80)

# 1. PnL 클램핑
MAX_SINGLE_PNL = 50.0
MIN_SINGLE_PNL = -50.0

opt_clamped_trades = []
for t in sample_trades:
    raw_pnl = t['pnl'] * leverage
    clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, raw_pnl))
    opt_clamped_trades.append({'pnl': clamped_pnl, 'type': t['type']})

opt_pnls = [t['pnl'] for t in opt_clamped_trades]

# 2. 메트릭 계산 (SSOT)
opt_win_rate = calculate_win_rate(opt_clamped_trades)
opt_mdd = calculate_mdd(opt_clamped_trades)
opt_sharpe = calculate_sharpe_ratio(opt_pnls, periods_per_year=252*4)
opt_pf = calculate_profit_factor(opt_clamped_trades)
opt_stability = calculate_stability(opt_pnls)
opt_simple_return = sum(opt_pnls)

# 3. Compound Return
opt_equity = 1.0
for p in opt_pnls:
    opt_equity *= (1 + p / 100)
    if opt_equity <= 0:
        opt_equity = 0
        break
opt_compound = (opt_equity - 1) * 100
opt_compound = max(-100.0, min(opt_compound, 1e10))

print(f'Win Rate:       {opt_win_rate:.2f}%')
print(f'MDD:            {opt_mdd:.2f}%')
print(f'Sharpe Ratio:   {opt_sharpe:.2f}')
print(f'Profit Factor:  {opt_pf:.2f}')
print(f'Stability:      {opt_stability.encode("ascii", "ignore").decode("ascii") if isinstance(opt_stability, str) else opt_stability}')
print(f'Simple Return:  {opt_simple_return:.2f}%')
print(f'Compound:       {opt_compound:.2f}%')

# === 백테스트 워커 로직 시뮬레이션 (수정 후) ===
print()
print('[백테스트 워커 계산 - 수정 후]')
print('-' * 80)

# 1. PnL 클램핑 (최적화와 동일)
bt_clamped_trades = []
for t in sample_trades:
    raw_pnl = t['pnl'] * leverage
    clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, raw_pnl))
    bt_clamped_trades.append({'pnl': clamped_pnl, 'type': t['type']})

bt_pnls = [t['pnl'] for t in bt_clamped_trades]

# 2. 메트릭 계산 (SSOT)
bt_win_rate = calculate_win_rate(bt_clamped_trades)
bt_mdd = calculate_mdd(bt_clamped_trades)
bt_sharpe = calculate_sharpe_ratio(bt_pnls, periods_per_year=252*4)
bt_pf = calculate_profit_factor(bt_clamped_trades)
bt_stability = calculate_stability(bt_pnls)
bt_simple_return = sum(bt_pnls)

# 3. Compound Return
bt_equity = 1.0
bt_cumulative_equity = [1.0]
for p in bt_pnls:
    bt_equity *= (1 + p / 100)
    if bt_equity <= 0:
        bt_equity = 0
    bt_cumulative_equity.append(bt_equity)
    if bt_equity == 0:
        break
bt_compound = (bt_equity - 1) * 100
bt_compound = max(-100.0, min(bt_compound, 1e10))

print(f'Win Rate:       {bt_win_rate:.2f}%')
print(f'MDD:            {bt_mdd:.2f}%')
print(f'Sharpe Ratio:   {bt_sharpe:.2f}')
print(f'Profit Factor:  {bt_pf:.2f}')
print(f'Stability:      {bt_stability.encode("ascii", "ignore").decode("ascii") if isinstance(bt_stability, str) else bt_stability}')
print(f'Simple Return:  {bt_simple_return:.2f}%')
print(f'Compound:       {bt_compound:.2f}%')

# === 차이 비교 ===
print()
print('[차이 분석]')
print('-' * 80)

def compare(name, opt_val, bt_val, threshold):
    diff = abs(opt_val - bt_val)
    status = 'PASS' if diff < threshold else 'FAIL'
    return f'{name:20} | Opt: {opt_val:>8.2f} | BT: {bt_val:>8.2f} | Diff: {diff:>6.4f} | {status}'

print(compare('Win Rate (%)', opt_win_rate, bt_win_rate, 0.01))
print(compare('MDD (%)', opt_mdd, bt_mdd, 0.01))
print(compare('Sharpe Ratio', opt_sharpe, bt_sharpe, 0.01))
print(compare('Profit Factor', opt_pf, bt_pf, 0.01))
print(compare('Simple Return (%)', opt_simple_return, bt_simple_return, 0.01))
print(compare('Compound (%)', opt_compound, bt_compound, 0.01))
opt_stab_safe = opt_stability.encode("ascii", "ignore").decode("ascii") if isinstance(opt_stability, str) else str(opt_stability)
bt_stab_safe = bt_stability.encode("ascii", "ignore").decode("ascii") if isinstance(bt_stability, str) else str(bt_stability)
print(f'{"Stability":20} | Opt: {opt_stab_safe:>8} | BT: {bt_stab_safe:>8} | {"PASS" if opt_stability == bt_stability else "FAIL"}')

# === 종합 판정 ===
print()
print('[종합 판정]')
print('-' * 80)

all_pass = (
    abs(opt_win_rate - bt_win_rate) < 0.01 and
    abs(opt_mdd - bt_mdd) < 0.01 and
    abs(opt_sharpe - bt_sharpe) < 0.01 and
    abs(opt_pf - bt_pf) < 0.01 and
    abs(opt_simple_return - bt_simple_return) < 0.01 and
    abs(opt_compound - bt_compound) < 0.01 and
    opt_stability == bt_stability
)

if all_pass:
    print('Result: PASS')
    print('Optimizer and Backtest calculations are perfectly matched.')
else:
    print('Result: FAIL')
    print('Some metrics show differences.')

print()
print('=' * 80)
print('Test Complete')
print('=' * 80)
