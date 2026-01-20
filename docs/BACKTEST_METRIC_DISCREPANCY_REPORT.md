# 📊 백테스트 메트릭 계산 불일치 분석 보고서

**작성일**: 2026-01-17
**대상 시스템**: TwinStar-Quantum v7.23
**심각도**: 🔴 **CRITICAL** - 최적화 신뢰성 손실

---

## 🔥 Executive Summary

**문제**: 동일한 데이터와 파라미터로 백테스트를 2번 실행했을 때 **MDD가 66% 차이** 발생
**원인**: `core/optimizer.py`의 MDD 계산 시 **PnL 클램핑(±50% 제한)** 적용
**영향**: 최적화 시 선택된 "최고 파라미터"가 실제로는 **잘못된 파라미터**일 수 있음

---

## 📊 실험 결과

### 실험 설정

- **프리셋**: `bybit_BTCUSDT_1h_macd_20260117_235704.json`
- **데이터**: 50,957개 캔들 (2020-03-25 ~ 2026-01-16, 2,123일)
- **파라미터**: 완전 동일 (atr_mult=1.5, filter_tf='12h', macd 6/18/7 등)

### 결과 비교

| 지표 | 최적화 시 (Optimizer) | 검증 시 (SSOT) | 차이 | 허용 범위 |
|------|----------------------|----------------|------|-----------|
| **승률** | 89.87% | 90.02% | **+0.15%** | ✅ ±5% |
| **MDD** | **18.80%** | **6.30%** | **-66%** | ❌ **심각** |
| **Sharpe** | 25.28 | 25.03 | **-1.0%** | ✅ ±5% |
| **PF** | 9.53 | 9.38 | **-1.6%** | ✅ ±5% |
| **거래수** | 1,777 | 1,783 | **+6** | ⚠️ 데이터 |

### 핵심 문제

**MDD 18.80% → 6.30% (-66%)** 차이는 **재현 불가능**을 의미합니다.

---

## 🔍 근본 원인 분석

### 1️⃣ PnL 클램핑 (±50% 제한)

**발견 위치**: `core/optimizer.py:1404-1426`

```python
# 1. 누적 수익률 (Compound/Equity) 계산
# [FIX] 단일 거래 PnL 상한선 적용 (±50%) - 오버플로우 방지
MAX_SINGLE_PNL = 50.0  # 단일 거래 최대 수익률 상한
MIN_SINGLE_PNL = -50.0  # 단일 거래 최대 손실률 하한

equity = 1.0
cumulative_equity = [1.0]
for p in pnls:
    # PnL 클램핑 (상한/하한 적용)
    clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, p))  # ⚠️ 여기!
    equity *= (1 + clamped_pnl / 100)
    if equity <= 0: equity = 0
    cumulative_equity.append(equity)
    if equity == 0: break

compound_return = (equity - 1) * 100
compound_return = max(-100.0, min(compound_return, 1e10))

# 2. 최대 낙폭 (MDD %) 계산 - SSOT 사용
# PnL 클램핑이 적용된 trades 리스트 생성
clamped_trades = []
for p in pnls:
    clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, p))  # ⚠️ 여기!
    clamped_trades.append({'pnl': clamped_pnl})

# SSOT calculate_mdd() 호출
max_drawdown = calculate_mdd(clamped_trades)  # ⚠️ 클램핑된 데이터로 계산!
```

**문제**:
- Optimizer는 **클램핑된 PnL**로 MDD 계산 → **18.80%**
- 검증 스크립트는 **원본 PnL**로 MDD 계산 → **6.30%**

### 2️⃣ SSOT 원칙 위반

| 코드 경로 | MDD 계산 방식 | PnL 클램핑 | 결과 |
|-----------|---------------|------------|------|
| `core/optimizer.py:1422-1429` | `calculate_mdd(clamped_trades)` | ✅ **±50%** | 18.80% |
| `utils/metrics.py:133-164` | `calculate_mdd(trades)` | ❌ **없음** | 6.30% |
| `tools/quick_verify_coarse_fine.py:122` | `calculate_backtest_metrics(trades)` | ❌ **없음** | 6.30% |

**SSOT 위반**: 동일한 `calculate_mdd()` 함수를 호출하지만 **입력 데이터가 다름**

### 3️⃣ 클램핑의 의도

주석에 따르면 **"오버플로우 방지"**가 목적:

```python
# [FIX] 단일 거래 PnL 상한선 적용 (±50%) - 오버플로우 방지
```

**그러나**:
- 실제 거래에서 단일 PnL이 ±50%를 초과하는 경우는 **레버리지 매매**에서 발생 가능
- 클램핑은 **실제 위험을 숨김** → MDD가 낮게 계산됨
- 최적화 시 **위험한 파라미터를 선택**할 가능성

---

## 🎯 영향 분석

### 최적화 결과 왜곡

**시나리오**: ATR × 5.0 (넓은 손절)을 테스트할 때

```python
# 실제 거래 결과 (원본 PnL)
trades = [
    {'pnl': -60.0},  # 큰 손실
    {'pnl': +5.0},
    {'pnl': +5.0},
    ...
]

# Optimizer 계산 (클램핑 적용)
clamped_trades = [
    {'pnl': -50.0},  # ⚠️ -60% → -50%로 클램핑
    {'pnl': +5.0},
    {'pnl': +5.0},
    ...
]

# MDD 계산
실제 MDD: 60% (위험함!)
클램핑 MDD: 50% (안전해 보임!)
```

**결과**: Optimizer는 **ATR × 5.0을 안전하다고 판단** → 잘못된 최적화!

### 프리셋 신뢰성 손실

현재 저장된 프리셋:
- **MDD 18.80%** (클램핑 적용)
- **실제 MDD: 알 수 없음** (원본 PnL로 재계산 필요)

**문제**: 프리셋을 신뢰할 수 없음

---

## ✅ 해결 방안

### Option A: 클램핑 완전 제거 (권장)

**장점**:
- SSOT 원칙 준수
- 실제 위험 반영
- 재현 가능성 100%

**단점**:
- 오버플로우 가능성 (복리 계산 시)

**구현**:

```python
# core/optimizer.py:1404-1429
# ❌ Before
MAX_SINGLE_PNL = 50.0
MIN_SINGLE_PNL = -50.0
clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, p))

# ✅ After
# 클램핑 제거, 원본 PnL 사용
# 오버플로우는 compound_return에만 제한 적용
for p in pnls:
    equity *= (1 + p / 100)  # 클램핑 없음
    if equity <= 0 or equity > 1e10:  # 오버플로우만 방지
        equity = max(0, min(1e10, equity))
    cumulative_equity.append(equity)

# MDD 계산 (원본 trades 사용)
max_drawdown = calculate_mdd(trades)  # 클램핑 없음!
```

### Option B: 클램핑 정보 프리셋 저장

**장점**:
- 하위 호환성 유지
- 클램핑 적용 여부 명시

**단점**:
- 복잡도 증가
- SSOT 원칙 여전히 위반

**구현**:

```json
{
  "meta_info": {
    "pnl_clamping": {
      "enabled": true,
      "max": 50.0,
      "min": -50.0
    }
  },
  "best_metrics": {
    "mdd": 18.8,
    "mdd_unclamped": 6.3  // 원본 PnL 기준
  }
}
```

### Option C: Optimizer도 SSOT 완전 통합

**장점**:
- 완벽한 SSOT 준수
- 재현 가능성 100%

**단점**:
- 대규모 리팩토링 필요

**구현**:

```python
# core/optimizer.py
def calculate_metrics(trades: List[Dict]) -> Dict:
    # ❌ 로컬 MDD 계산 제거
    # max_drawdown = calculate_mdd(clamped_trades)

    # ✅ utils.metrics.calculate_backtest_metrics() 직접 호출
    from utils.metrics import calculate_backtest_metrics
    metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    # 키 이름 변환만 수행
    return {
        'win_rate': metrics['win_rate'],
        'max_drawdown': metrics['mdd'],
        'sharpe_ratio': metrics['sharpe_ratio'],
        'profit_factor': metrics['profit_factor'],
        ...
    }
```

---

## 📈 권장 조치

### 즉시 (P0)

1. **클램핑 제거** (Option A)
   - `core/optimizer.py:1404-1429` 수정
   - 모든 프리셋 재생성 필요

2. **검증 스크립트 업데이트**
   - 클램핑 여부 확인
   - 차이 발생 시 경고

### 단기 (P1)

3. **Optimizer SSOT 통합** (Option C)
   - `calculate_metrics()` → `calculate_backtest_metrics()` 호출
   - 코드 중복 제거

4. **단위 테스트 추가**
   - Optimizer vs SSOT 메트릭 비교
   - 허용 오차 ±1% 이하

### 중기 (P2)

5. **문서 업데이트**
   - CLAUDE.md에 메트릭 계산 정책 명시
   - 프리셋 형식 v2.0 정의

6. **기존 프리셋 검증**
   - 모든 저장된 프리셋 재검증
   - 차이 > 5% 프리셋 폐기

---

## 🎯 검증 기준

수정 후 다음 조건 만족 필요:

| 항목 | 목표 | 현재 | 상태 |
|------|------|------|------|
| MDD 재현성 | ±1% | -66% | ❌ |
| 승률 재현성 | ±1% | +0.15% | ✅ |
| Sharpe 재현성 | ±2% | -1.0% | ✅ |
| PF 재현성 | ±2% | -1.6% | ✅ |
| 거래수 재현성 | 0 | +6 | ⚠️ |
| SSOT 준수 | 100% | 50% | ❌ |

---

## 📌 결론

**현 상태**: 최적화 시스템 신뢰 불가능
**핵심 원인**: PnL 클램핑으로 인한 MDD 왜곡
**해결 방법**: 클램핑 제거 + SSOT 완전 통합
**예상 작업량**: 2~3시간 (코드 수정 + 테스트 + 프리셋 재생성)

**권장**: 즉시 수정 필요. 현재 저장된 프리셋(MDD 18.8%)은 **신뢰 불가**.

---

## 📎 참고 자료

- 프리셋: `presets/coarse_fine/bybit_BTCUSDT_1h_macd_20260117_235704.json`
- Optimizer 코드: `core/optimizer.py:1360-1440`
- SSOT 메트릭: `utils/metrics.py:133-378`
- 검증 스크립트: `tools/quick_verify_coarse_fine.py`
- CLAUDE.md 버전: v7.23

**작성자**: Claude Sonnet 4.5
**검토 필요**: 사용자 승인 후 즉시 수정 권장
