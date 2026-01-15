# 실시간 매매 vs 백테스트/최적화 메트릭 비교

**작성일**: 2026-01-15
**목적**: 실시간 매매, 백테스트, 최적화에서 PnL 클램핑 및 메트릭 계산 적용 범위 명확화

---

## 🎯 핵심 질문

**"PnL 클램핑 및 SSOT 메트릭이 웹소켓 실시간 매매에도 적용되는가?"**

**답변**: **부분적으로만 적용됨**

---

## 📊 시스템별 계산식 적용 범위

### 1. 백테스트 시스템 (`ui/widgets/backtest/worker.py`)

**적용 범위**: ✅ **완전 적용**

```python
# PnL 클램핑 (361-377줄)
MAX_SINGLE_PNL = 50.0
MIN_SINGLE_PNL = -50.0

leveraged_trades = []
for t in trades:
    raw_pnl = t.get('pnl', 0) * leverage
    clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, raw_pnl))
    leveraged_trades.append({**t, 'pnl': clamped_pnl})

# SSOT 메트릭 (376-380줄)
win_rate = calculate_win_rate(leveraged_trades)
mdd = calculate_mdd(leveraged_trades)
sharpe = calculate_sharpe_ratio(pnls, periods_per_year=252*4)
pf = calculate_profit_factor(leveraged_trades)
stability = calculate_stability(pnls)
```

**목적**: 백테스트 **결과 표시 및 등급 계산**

---

### 2. 최적화 시스템 (`core/optimizer.py`)

**적용 범위**: ✅ **완전 적용**

```python
# PnL 클램핑 (1179-1191줄)
MAX_SINGLE_PNL = 50.0
MIN_SINGLE_PNL = -50.0

equity = 1.0
for p in pnls:
    clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, p))
    equity *= (1 + clamped_pnl / 100)
    if equity <= 0:
        equity = 0
        break

# SSOT 메트릭 (1174-1215줄)
win_rate = calculate_win_rate(trades)
mdd = calculate_mdd(clamped_trades)
sharpe = calculate_sharpe_ratio(pnl_series.tolist(), periods_per_year=252*4)
pf = calculate_profit_factor(trades_for_pf)
stability = calculate_stability(pnls)
```

**목적**: 최적화 **파라미터 필터링 및 순위 결정**

---

### 3. 실시간 매매 시스템 (`core/unified_bot.py`)

**적용 범위**: ❌ **적용 안됨** (또는 간접적)

#### 실시간 매매의 특징

```python
# unified_bot.py - Radical Delegation 아키텍처

class UnifiedBot:
    def __init__(self, ...):
        # 모듈형 컴포넌트 위임
        self.mod_state = BotStateManager()        # 상태 관리
        self.mod_data = BotDataManager()          # 데이터 관리
        self.mod_signal = SignalProcessor()       # 신호 처리
        self.mod_order = OrderExecutor()          # 주문 실행
        self.mod_position = PositionManager()     # 포지션 관리

    def run(self):
        """실시간 매매 루프"""
        while self.running:
            # 1. 웹소켓으로 실시간 가격 수신
            candle = self.mod_data.get_latest_candle()

            # 2. 신호 생성 (전략 엔진)
            signal = self.mod_signal.check_signal(candle, self.params)

            # 3. 주문 실행
            if signal:
                self.mod_order.execute(signal)

            # 4. 포지션 관리
            self.mod_position.update_positions()

            # ❌ 메트릭 계산 없음 (실시간 거래는 개별 거래 단위)
            # ❌ PnL 클램핑 없음 (실제 거래는 거래소에서 체결된 그대로)
```

#### 실시간 매매에서 메트릭이 필요 없는 이유

1. **개별 거래 실행**: 각 거래는 독립적으로 실행됨
   - 메트릭은 **거래 집합**에 대한 통계 (백테스트/최적화용)
   - 실시간은 **단일 거래** 단위로 동작

2. **거래소 제약**: 실제 체결가는 거래소가 결정
   - PnL 클램핑을 적용할 수 없음 (실제 체결가 그대로 사용)
   - 예: 100% 수익이 나면 그대로 100% 수익

3. **리스크 관리는 다른 방식**:
   - Stop Loss / Take Profit (주문 레벨에서 제한)
   - 레버리지 제한 (진입 시점에 제한)
   - 포지션 사이즈 제한 (자본 관리)

---

## 🔄 간접 적용: 실시간 → 백테스트 연동

실시간 매매 **후** 결과 분석 시에는 SSOT 메트릭이 적용됩니다:

```python
# 실시간 매매 완료 후
trades_history = bot.get_trade_history()  # 실제 체결된 거래 내역

# 백테스트 워커와 동일한 메트릭 계산 (선택 사항)
from utils.metrics import (
    calculate_win_rate,
    calculate_mdd,
    calculate_sharpe_ratio,
    calculate_profit_factor
)

win_rate = calculate_win_rate(trades_history)
mdd = calculate_mdd(trades_history)
sharpe = calculate_sharpe_ratio([t['pnl'] for t in trades_history])
pf = calculate_profit_factor(trades_history)

# GUI 대시보드에 표시
dashboard.update_metrics(win_rate, mdd, sharpe, pf)
```

**위치**: GUI 대시보드, 거래 내역 리포트 등

---

## 📋 시스템별 비교표

| 항목 | 백테스트 | 최적화 | 실시간 매매 |
|------|---------|--------|-----------|
| **PnL 클램핑** | ✅ 적용 (±50%) | ✅ 적용 (±50%) | ❌ 미적용 (실제 체결가) |
| **SSOT 메트릭** | ✅ 사용 | ✅ 사용 | ❌ 미사용 (실시간은 개별 거래) |
| **목적** | 과거 데이터 분석 | 파라미터 최적화 | 실제 거래 실행 |
| **데이터 소스** | Parquet 파일 | Parquet 파일 | 웹소켓 (실시간) |
| **계산 단위** | 거래 집합 (수백~수천개) | 거래 집합 | 단일 거래 |
| **레버리지** | 시뮬레이션 (배수) | 시뮬레이션 (배수) | 실제 적용 (거래소) |
| **리스크 관리** | MDD, 승률 필터 | MDD, 승률 필터 | SL/TP, 포지션 사이즈 |

---

## 🛠 실시간 매매의 리스크 관리 방식

### 1. 진입 시점 제한

```python
# core/order_executor.py
def place_order(self, signal: Signal):
    # 레버리지 제한
    if self.leverage > self.max_leverage:
        logger.warning(f"레버리지 초과: {self.leverage} > {self.max_leverage}")
        return False

    # 포지션 사이즈 제한
    if position_size > self.max_position_size:
        position_size = self.max_position_size

    # 주문 실행
    self.exchange.place_order(signal.side, position_size)
```

### 2. Stop Loss / Take Profit

```python
# core/position_manager.py
def set_stop_loss_take_profit(self, position: Position):
    # ATR 기반 SL/TP 설정
    atr = self.calculate_atr()

    # Stop Loss: 진입가 ± (ATR × 배수)
    sl_price = position.entry_price - (atr * self.sl_multiplier)

    # Take Profit: 진입가 ± (ATR × 배수)
    tp_price = position.entry_price + (atr * self.tp_multiplier)

    # 거래소에 SL/TP 주문 등록
    self.exchange.set_stop_loss(position, sl_price)
    self.exchange.set_take_profit(position, tp_price)
```

### 3. 동적 포지션 관리

```python
# core/position_manager.py
def update_positions(self):
    for position in self.positions:
        # 실시간 PnL 계산
        current_price = self.get_current_price(position.symbol)
        pnl = self.calculate_position_pnl(position, current_price)

        # 손실 제한 (예: -10% 도달 시 강제 청산)
        if pnl < -10.0:
            logger.warning(f"손실 한도 도달: {pnl:.2f}%")
            self.close_position(position)

        # Trailing Stop (수익 보호)
        if pnl > 5.0:
            self.update_trailing_stop(position, current_price)
```

---

## ✅ 결론

### PnL 클램핑 및 SSOT 메트릭 적용 범위

1. **백테스트**: ✅ **완전 적용**
   - 과거 거래 데이터 분석
   - 등급 계산 (S/A/B/C/F)
   - 필터링 (MDD≤20%, 승률≥75%)

2. **최적화**: ✅ **완전 적용**
   - 파라미터 조합 평가
   - 고품질 파라미터 선별
   - 순위 정렬

3. **실시간 매매**: ❌ **직접 적용 안됨**
   - 개별 거래 단위로 동작
   - 실제 체결가 그대로 사용 (클램핑 불가)
   - 리스크 관리는 SL/TP, 포지션 사이즈로 제어

4. **실시간 매매 결과 분석**: ⚠️ **간접 적용 가능**
   - 거래 완료 후 GUI 대시보드에서 메트릭 표시
   - 일일/주간/월간 리포트 생성
   - 실제 거래 성과 평가

---

## 🎯 핵심 이해

**백테스트/최적화**:
- "이 파라미터가 과거에 얼마나 좋았을까?" → 메트릭 필요
- PnL 클램핑으로 극단적 시나리오 방지 → 현실적 평가

**실시간 매매**:
- "지금 이 신호로 거래할까?" → 개별 판단
- 실제 거래는 거래소가 체결 → 클램핑 불가능
- 리스크는 SL/TP, 포지션 사이즈로 제어

**핵심**: 백테스트/최적화는 **집합 분석**, 실시간은 **개별 실행**

---

## 🔍 FAQ

### Q1: 실시간 매매에서 +100% 수익이 나면?
**A**: 실제로 100% 수익으로 기록됩니다. 클램핑 없음.
- 백테스트/최적화: 50%로 클램핑 (시뮬레이션)
- 실시간 매매: 100% 그대로 (실제 체결)

### Q2: 실시간 매매의 리스크 관리는?
**A**:
1. Stop Loss (손실 제한)
2. Take Profit (수익 확정)
3. 포지션 사이즈 제한
4. 레버리지 제한
5. Trailing Stop (수익 보호)

### Q3: 실시간 매매 결과도 백테스트처럼 분석할 수 있나?
**A**: 네. 거래 완료 후 동일한 SSOT 메트릭으로 분석 가능합니다.
```python
# 실시간 매매 완료 후
trades = bot.get_trade_history()
metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)
print(f"실제 거래 승률: {metrics['win_rate']:.2f}%")
print(f"실제 거래 MDD: {metrics['mdd']:.2f}%")
```

### Q4: 백테스트 S등급 파라미터를 실시간에 쓰면 같은 결과가 나오나?
**A**: **아니요**. 백테스트는 과거 데이터, 실시간은 미래 시장.
- 백테스트: 과거 성과 평가 (S등급 = 과거에 좋았음)
- 실시간: 미래 예측 (S등급이라도 미래는 다를 수 있음)
- **목적**: 백테스트는 **파라미터 검증**, 실시간은 **실제 거래**

---

**문서 버전**: v1.0
**작성**: Claude Sonnet 4.5
**요약**: PnL 클램핑 및 SSOT 메트릭은 백테스트/최적화에만 적용, 실시간 매매는 SL/TP로 리스크 관리
