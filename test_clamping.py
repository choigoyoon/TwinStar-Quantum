"""PnL 클램핑 및 계산식 테스트"""
from utils.metrics import calculate_mdd, calculate_win_rate, calculate_sharpe_ratio, calculate_profit_factor

# 테스트 데이터 (극단적 수익/손실 포함)
trades = [
    {'pnl': 100.0, 'type': 'Long'},   # +100%
    {'pnl': -80.0, 'type': 'Short'},  # -80%
    {'pnl': 30.0, 'type': 'Long'},    # +30%
    {'pnl': -20.0, 'type': 'Short'},  # -20%
    {'pnl': 10.0, 'type': 'Long'},    # +10%
]

print('=' * 80)
print('PnL 클램핑 및 메트릭 계산 테스트')
print('=' * 80)

# 1. PnL 클램핑 (레버리지 2배)
print('\n[1] PnL 클램핑 테스트 (레버리지 2배)')
print('-' * 80)
leverage = 2
MAX_SINGLE_PNL = 50.0
MIN_SINGLE_PNL = -50.0

clamped_trades = []
for t in trades:
    raw_pnl = t['pnl'] * leverage
    clamped = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, raw_pnl))
    print(f"원본: {t['pnl']:>7.1f}% x {leverage} = {raw_pnl:>7.1f}% -> 클램핑: {clamped:>7.1f}%")
    clamped_trades.append({'pnl': clamped, 'type': t['type']})

# 2. 메트릭 계산 (SSOT)
print('\n[2] 메트릭 계산 (utils.metrics SSOT)')
print('-' * 80)
win_rate = calculate_win_rate(clamped_trades)
mdd = calculate_mdd(clamped_trades)
pnls = [t['pnl'] for t in clamped_trades]
sharpe = calculate_sharpe_ratio(pnls, periods_per_year=252*4)
pf = calculate_profit_factor(clamped_trades)

print(f'승률 (Win Rate):        {win_rate:.2f}%')
print(f'최대 낙폭 (MDD):        {mdd:.2f}%')
print(f'샤프 비율 (Sharpe):     {sharpe:.2f}')
print(f'손익 비율 (PF):         {pf:.2f}')

# 3. 누적 수익률 계산
print('\n[3] 누적 수익률 계산')
print('-' * 80)
equity = 1.0
equity_curve = [1.0]
print(f'초기 자본: {equity:.4f}')
for i, p in enumerate(pnls):
    prev_equity = equity
    equity *= (1 + p / 100)
    if equity <= 0:
        equity = 0
    equity_curve.append(equity)
    print(f'거래 {i+1}: {p:>7.1f}% -> Equity: {prev_equity:.4f} -> {equity:.4f}')
    if equity == 0:
        break

compound_return = (equity - 1) * 100
compound_return = max(-100.0, min(compound_return, 1e10))
print(f'\n최종 Equity: {equity:.4f}')
print(f'누적 수익률: {compound_return:.2f}%')

# 4. Direction 필터 테스트
print('\n[4] Direction 필터 테스트')
print('-' * 80)
for direction in ['Both', 'Long', 'Short']:
    if direction != 'Both':
        filtered = [t for t in clamped_trades if t['type'] == direction]
    else:
        filtered = clamped_trades
    print(f'{direction:>6}: {len(filtered)}개 거래')

# 5. 필터 기준 테스트
print('\n[5] 필터 기준 테스트')
print('-' * 80)
passes_filter = (
    mdd <= 20.0 and
    win_rate >= 75.0 and
    len(clamped_trades) >= 10
)

print(f'MDD <= 20%:       {mdd:.2f}% -> {"통과" if mdd <= 20.0 else "실패"}')
print(f'승률 >= 75%:      {win_rate:.2f}% -> {"통과" if win_rate >= 75.0 else "실패"}')
print(f'거래 >= 10개:     {len(clamped_trades)}개 -> {"통과" if len(clamped_trades) >= 10 else "실패"}')
print(f'\n전체 필터 통과:  {"예" if passes_filter else "아니오"}')

print('\n' + '=' * 80)
print('테스트 완료')
print('=' * 80)
