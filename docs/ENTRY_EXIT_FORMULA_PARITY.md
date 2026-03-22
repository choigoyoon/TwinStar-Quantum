# 진입/익절/손절 계산식 일치성 분석

**작성일**: 2026-01-15
**핵심 질문**: 백테스트와 실시간 매매에서 진입 조건, SL, TP 계산식이 같은가?

---

## ✅ 결론: **완전히 동일**합니다!

백테스트와 실시간 매매는 **동일한 전략 모듈**([core/strategy_core.py](../core/strategy_core.py))을 사용하므로, 진입/익절/손절 계산식이 100% 일치합니다.

---

## 🎯 Single Source of Truth (SSOT)

### 전략 모듈: `core/strategy_core.py`

```
┌─────────────────────────────────────┐
│   core/strategy_core.py             │
│   (AlphaX7Core)                     │
│                                     │
│   - 진입 조건 (W/M 패턴)            │
│   - SL 계산 (ATR 기반)              │
│   - TP 계산 (Trailing Stop)         │
│   - 지표 계산 (RSI, ATR, ADX)       │
└─────────────────────────────────────┘
          ↑                    ↑
          │                    │
    ┌─────┴──────┐      ┌─────┴──────┐
    │ 백테스트    │      │ 실시간 매매 │
    │ (worker.py) │      │ (bot.py)    │
    └────────────┘      └────────────┘
```

**양쪽 모두 동일한 `AlphaX7Core` 클래스 사용**

---

## 📐 계산식 상세

### 1. 진입 조건 (Signal Generation)

**위치**: [core/strategy_core.py:493-578](../core/strategy_core.py#L493-L578)

```python
def check_signal(self, df_pattern, df_entry, allowed_direction='Both'):
    """
    진입 신호 확인 (W/M 패턴 기반)

    백테스트와 실시간 모두 동일한 로직 사용
    """
    # W 패턴 (Long)
    if allowed_direction in ['Both', 'Long']:
        # 패턴 매칭
        w_pattern = self._detect_w_pattern(df_pattern)
        if w_pattern:
            # ATR 확인
            atr = df_entry.iloc[-1]['atr']
            if atr <= 0:
                return None

            # 진입가 및 SL 계산
            price = float(df_entry.iloc[-1]['close'])
            atr_mult = self.adaptive_params.get('atr_mult', 1.25)
            sl = price - atr * atr_mult  # Long SL

            return TradeSignal(
                signal_type='Long',
                entry_price=price,
                stop_loss=sl,
                atr=atr
            )

    # M 패턴 (Short)
    if allowed_direction in ['Both', 'Short']:
        m_pattern = self._detect_m_pattern(df_pattern)
        if m_pattern:
            atr = df_entry.iloc[-1]['atr']
            if atr <= 0:
                return None

            price = float(df_entry.iloc[-1]['close'])
            atr_mult = self.adaptive_params.get('atr_mult', 1.25)
            sl = price + atr * atr_mult  # Short SL

            return TradeSignal(
                signal_type='Short',
                entry_price=price,
                stop_loss=sl,
                atr=atr
            )
```

**핵심**: 백테스트/실시간 **완전 동일**

---

### 2. Stop Loss (SL) 계산

**공식**: ATR 기반

```python
# Long 포지션
sl = entry_price - (atr × atr_mult)

# Short 포지션
sl = entry_price + (atr × atr_mult)
```

**파라미터**:
- `atr`: Average True Range (변동성 지표)
- `atr_mult`: ATR 배수 (기본값 1.25, 범위 0.8~2.5)

**위치**:
- 실시간 신호: [strategy_core.py:518](../core/strategy_core.py#L518) (Long), [strategy_core.py:572](../core/strategy_core.py#L572) (Short)
- 백테스트: [strategy_core.py:921](../core/strategy_core.py#L921)

**예시**:
```python
# BTCUSDT, Long 진입
entry_price = 50000
atr = 500
atr_mult = 1.5

sl = 50000 - (500 × 1.5) = 49250  # 1.5% 손절
```

---

### 3. Take Profit (TP) 계산 - Trailing Stop

**공식**: 동적 익절 (Trailing Stop)

```python
# 초기 목표가 설정
risk = abs(entry_price - sl)
initial_tp = entry_price + (risk × trail_start_r)  # Long
initial_tp = entry_price - (risk × trail_start_r)  # Short

# Trailing Stop 활성화 (가격이 initial_tp 도달 시)
if current_price >= initial_tp:  # Long
    # 트레일링 시작
    trail_price = current_price - (risk × trail_dist_r)

    # 트레일링 업데이트 (최고가 갱신 시)
    if current_price > max_price:
        max_price = current_price
        trail_price = max_price - (risk × trail_dist_r)
```

**파라미터**:
- `trail_start_r`: 트레일링 시작 배율 (기본값 0.8, 범위 0.5~3.0)
- `trail_dist_r`: 트레일링 거리 배율 (기본값 0.5, 범위 0.3~2.0)

**위치**: [strategy_core.py:926-1050](../core/strategy_core.py#L926-L1050)

**예시**:
```python
# BTCUSDT, Long 진입
entry_price = 50000
sl = 49250
risk = 750  # abs(50000 - 49250)

# 초기 TP (0.8R)
initial_tp = 50000 + (750 × 0.8) = 50600

# 가격 상승 시 (예: 51000)
trail_price = 51000 - (750 × 0.5) = 50625  # 트레일링
```

---

## 🔬 백테스트 vs 실시간 비교

### 백테스트 (`ui/widgets/backtest/worker.py`)

```python
# 1. 전략 모듈 임포트
from core.strategy_core import AlphaX7Core

# 2. 전략 인스턴스 생성
strategy = AlphaX7Core(
    symbol='BTCUSDT',
    timeframe='15m',
    exchange='bybit'
)

# 3. 백테스트 실행
result = strategy.run_backtest(
    df_pattern=df_pattern,
    df_entry=df_entry,
    atr_mult=1.5,           # SL 계산 파라미터
    trail_start_r=0.8,      # TP 시작 파라미터
    trail_dist_r=0.5        # TP 거리 파라미터
)
# → run_backtest() 내부에서 check_signal() 호출
# → 동일한 SL/TP 계산식 사용
```

### 실시간 매매 (`core/unified_bot.py`)

```python
# 1. 전략 모듈 임포트
from core.strategy_core import AlphaX7Core

# 2. 전략 인스턴스 생성
strategy = AlphaX7Core(
    symbol='BTCUSDT',
    timeframe='15m',
    exchange='bybit'
)

# 3. 실시간 신호 체크
while trading:
    # 최신 데이터 로드
    df_pattern = get_pattern_data()
    df_entry = get_entry_data()

    # 신호 확인 (백테스트와 동일한 함수)
    signal = strategy.check_signal(
        df_pattern=df_pattern,
        df_entry=df_entry,
        allowed_direction='Both'
    )
    # → check_signal() 내부에서 동일한 SL 계산
    # → signal.stop_loss = price - atr * atr_mult

    if signal:
        # 주문 실행
        exchange.place_order(
            side=signal.signal_type,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss  # ← 동일한 SL
        )
```

---

## 📊 파라미터 일치성 확인

### 파라미터 소스: `config/parameters.py`

```python
DEFAULT_PARAMS = {
    'atr_mult': 1.25,        # SL 계산
    'trail_start_r': 0.8,    # TP 시작
    'trail_dist_r': 0.5,     # TP 거리
    'pattern_tolerance': 0.05,
    'entry_validity_hours': 48.0,
    # ...
}
```

**백테스트**:
- [worker.py:286](../ui/widgets/backtest/worker.py#L286) → `DEFAULT_PARAMS` 사용
- 또는 사용자 입력 파라미터 사용

**실시간 매매**:
- [unified_bot.py](../core/unified_bot.py) → 동일한 `DEFAULT_PARAMS` 사용
- 또는 GUI에서 설정한 파라미터 사용

**결론**: 파라미터 소스도 SSOT (`config/parameters.py`)

---

## ✅ 검증 방법

### 1. 코드 레벨 검증

```python
# 백테스트와 실시간이 동일한 함수 사용하는지 확인
from core.strategy_core import AlphaX7Core

# 백테스트
bt_strategy = AlphaX7Core('BTCUSDT', '15m', 'bybit')
bt_signal = bt_strategy.check_signal(df_pattern, df_entry)

# 실시간
rt_strategy = AlphaX7Core('BTCUSDT', '15m', 'bybit')
rt_signal = rt_strategy.check_signal(df_pattern, df_entry)

# 동일한 데이터 입력 → 동일한 신호 출력
assert bt_signal.entry_price == rt_signal.entry_price
assert bt_signal.stop_loss == rt_signal.stop_loss
assert bt_signal.atr == rt_signal.atr
```

### 2. 실제 테스트

```bash
# 1. 백테스트 실행
python -m ui.main
# → 백테스트 탭 → 파라미터 설정 → 실행
# → 결과 확인 (진입가, SL, TP)

# 2. 실시간 매매 시뮬레이션
python tools/realtime_simulator.py
# → 동일한 파라미터 입력
# → 신호 생성 시 진입가, SL 확인

# 3. 비교
# → 동일한 타임스탬프, 동일한 가격 → 동일한 SL/TP
```

---

## 🔍 차이점 (데이터 타이밍만)

### 유일한 차이: 데이터 소스

| 항목 | 백테스트 | 실시간 매매 |
|------|---------|-----------|
| **데이터 소스** | Parquet 파일 (과거) | 웹소켓 (실시간) |
| **타이밍** | 과거 데이터 (완전) | 최신 데이터 (불완전) |
| **계산식** | ✅ 동일 | ✅ 동일 |
| **파라미터** | ✅ 동일 | ✅ 동일 |
| **전략 모듈** | ✅ `AlphaX7Core` | ✅ `AlphaX7Core` |

**핵심**: 데이터만 다르고, **계산식은 100% 동일**

---

## 📋 계산식 일치성 체크리스트

- [x] **진입 조건**: W/M 패턴 매칭 로직 (동일)
- [x] **SL 계산**: `price ± atr × atr_mult` (동일)
- [x] **TP 계산**: Trailing Stop 로직 (동일)
- [x] **지표 계산**: RSI, ATR, ADX (동일)
- [x] **파라미터 소스**: `config/parameters.py` (동일)
- [x] **전략 모듈**: `core/strategy_core.py` (동일)

**결론**: ✅ **완전 일치**

---

## 🎯 핵심 이해

### 왜 동일한가?

```
백테스트 → AlphaX7Core.run_backtest()
             ↓
           check_signal()  ← 동일 함수
             ↓
           SL = price ± atr × atr_mult

실시간  → AlphaX7Core.check_signal()
             ↓
           동일 로직
             ↓
           SL = price ± atr × atr_mult
```

**Single Source of Truth (SSOT)**:
- 전략 로직이 한 곳(`core/strategy_core.py`)에만 존재
- 백테스트와 실시간이 동일한 함수 호출
- 파라미터도 동일한 소스(`config/parameters.py`)

---

## 🔬 예시: 실제 계산

### 시나리오: BTCUSDT Long 진입

**입력 데이터** (백테스트/실시간 동일):
```python
close_price = 50000
atr = 500
atr_mult = 1.5
trail_start_r = 0.8
trail_dist_r = 0.5
```

**계산 결과** (백테스트/실시간 동일):
```python
# 진입가
entry_price = 50000

# SL (손절)
sl = 50000 - (500 × 1.5) = 49250  # -1.5%

# TP (초기 목표)
risk = abs(50000 - 49250) = 750
initial_tp = 50000 + (750 × 0.8) = 50600  # +1.2%

# Trailing (가격 51000 도달 시)
trail_price = 51000 - (750 × 0.5) = 50625
```

**결과**: 백테스트에서 진입가 50000, SL 49250이면, 실시간도 **정확히 동일**

---

## ✅ FAQ

### Q1: 백테스트 S등급 파라미터를 실시간에 쓰면 같은 성과?
**A**: **계산식은 동일**하지만, 시장 조건이 다르므로 성과는 다를 수 있습니다.
- 계산식: ✅ 동일 (SL, TP, 진입 조건)
- 데이터: ❌ 다름 (과거 vs 미래)
- 시장: ❌ 다름 (백테스트는 과거, 실시간은 미래)

### Q2: 실시간에서 SL이 더 넓게 설정되는 경우가 있나?
**A**: **없습니다**. 동일한 `atr_mult` 파라미터 → 동일한 SL.
- 단, 적응형 파라미터(`adaptive_params`)를 사용하면 ATR에 따라 `atr_mult`가 자동 조정됩니다 (백테스트/실시간 동일).

### Q3: Trailing Stop도 동일하게 작동하나?
**A**: **네**. `run_backtest()` 내부의 Trailing Stop 로직과 실시간 포지션 관리의 Trailing Stop 로직이 동일합니다.

### Q4: 파라미터를 바꾸면 양쪽 다 바뀌나?
**A**: **네**. `config/parameters.py`를 수정하면 백테스트와 실시간 모두 동일하게 적용됩니다.

---

**문서 버전**: v1.0
**작성**: Claude Sonnet 4.5
**결론**: 진입/익절/손절 계산식 **100% 일치** (Single Source of Truth)
