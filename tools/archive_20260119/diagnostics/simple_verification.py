"""
간단 검증 스크립트 - 수수료 및 기본 기능 테스트
"""

# 수수료 검증 (SSOT)
from config.constants import SLIPPAGE, FEE, TOTAL_COST

round_trip = TOTAL_COST * 2 * 100  # 왕복 %
print("=" * 80)
print("TwinStar-Quantum 수수료 검증")
print("=" * 80)
print(f"\n슬리피지: {SLIPPAGE * 100:.4f}%")
print(f"거래 수수료: {FEE * 100:.4f}%")
print(f"편도 총 비용: {TOTAL_COST * 100:.4f}%")
print(f"왕복 총 비용: {round_trip:.4f}%")
print(f"목표값: 0.23%")
print(f"차이: {round_trip - 0.23:.4f}%")
result_text = "[OK] 일치" if abs(round_trip - 0.23) < 0.01 else "[ERROR] 불일치"
print(f"\n결과: {result_text}")

if abs(round_trip - 0.23) >= 0.01:
    # 수정 필요
    needed_fee = (0.23 / 200) - SLIPPAGE
    print(f"\n[WARNING] 수정 필요:")
    print(f"  FEE = {needed_fee:.6f} (현재: {FEE})")
    print(f"  또는")
    needed_total = 0.23 / 200
    print(f"  TOTAL_COST = {needed_total:.6f} (현재: {TOTAL_COST})")

print("\n" + "=" * 80)
print("손익 계산 예시")
print("=" * 80)

# 손익 계산 함수
def calculate_pnl(entry_price, exit_price, size, direction, leverage=1):
    """손익 계산 (수수료 포함)"""
    if direction == 'Long':
        raw_pnl = (exit_price - entry_price) / entry_price * size * leverage
    else:
        raw_pnl = (entry_price - exit_price) / entry_price * size * leverage

    # 수수료 차감
    total_fee = size * TOTAL_COST * 2  # 진입 + 청산
    return raw_pnl - total_fee

# 예시 1: Long 포지션 (+5% 수익)
entry = 40000.0
exit_long = entry * 1.05
size = 1000.0
leverage = 10

pnl_long = calculate_pnl(entry, exit_long, size, 'Long', leverage)
print(f"\n[예시 1] Long 포지션")
print(f"  진입: ${entry:,.2f}")
print(f"  청산: ${exit_long:,.2f} (+5%)")
print(f"  크기: ${size:,.2f}")
print(f"  레버리지: {leverage}x")
print(f"  순손익: ${pnl_long:,.2f}")
print(f"  수익률: {(pnl_long / size) * 100:.2f}%")

# 예시 2: Short 포지션 (-3% 손실)
exit_short = entry * 1.03  # 가격 상승 = Short 손실
pnl_short = calculate_pnl(entry, exit_short, size, 'Short', leverage)
print(f"\n[예시 2] Short 포지션")
print(f"  진입: ${entry:,.2f}")
print(f"  청산: ${exit_short:,.2f} (+3% 가격 상승)")
print(f"  크기: ${size:,.2f}")
print(f"  레버리지: {leverage}x")
print(f"  순손익: ${pnl_short:,.2f}")
print(f"  손실률: {(pnl_short / size) * 100:.2f}%")

# 손익분기점 계산
breakeven_move = (FEE + SLIPPAGE) * 2  # 진입 + 청산
print(f"\n손익분기점: {breakeven_move * 100:.4f}%")

# 손익분기점 테스트
exit_breakeven = entry * (1 + breakeven_move)
pnl_breakeven = calculate_pnl(entry, exit_breakeven, size, 'Long', leverage)
print(f"손익분기 @ ${exit_breakeven:,.2f}: ${pnl_breakeven:.2f}")

print("\n" + "=" * 80)
print("[OK] 검증 완료")
print("=" * 80)
