# ADX 전략 비교 분석

## 전략 타입 차이

### 중요: 프리셋과 최적화의 전략이 다름!

| 항목 | 프리셋 | 현재 최적화 |
|------|--------|-----------|
| **전략 타입** | `adxdi` | `adx` |
| **전략 클래스** | 레거시 (Stochastic 포함) | AlphaX7Core |
| **신호 생성** | ADX + Stochastic + DI | ADX + DI만 |

---

## 프리셋 상세 (adxdi)

**파일**: `config/presets/bybit_btcusdt_1h_adxdi.json`

**생성 날짜**: 2026-01-13 05:47:31

**성능**:
```json
{
  "trades": 2572,
  "win_rate": 78.81%,
  "simple_pnl": 1938.05%,
  "max_drawdown": 11.05%,
  "profit_factor": 0,  ← ⚠️ 계산 오류
  "grade": "C"
}
```

**파라미터**:
```json
{
  "atr_mult": 1.5,
  "trail_start": 1.2,
  "trail_dist": 0.03,
  "tolerance": 0.1,
  "adx_min": 10,           ← ADX 최소 임계값
  "stoch_long_max": 50,    ← Stochastic 매수 조건
  "stoch_short_min": 50,   ← Stochastic 매도 조건
  "use_downtrend_filter": true
}
```

---

## 현재 최적화 결과 (adx)

**전략**: AlphaX7Core with `strategy_type='adx'`

**성능** (3회 평균):
```
trades: 679-680
win_rate: 90.1-91.3%
sharpe_ratio: 24.45
max_drawdown: 22.06-25.71%
profit_factor: 10.93-11.74
```

**파라미터**:
```python
{
  'atr_mult': 1.2,
  'trail_start_r': 0.8,
  'trail_dist_r': 0.015,
  'entry_validity_hours': 57.6,
  'adx_period': 10-14,
  'adx_threshold': 18.0-25.0  ← ADX 임계값 (프리셋보다 높음)
}
```

---

## 차이점 분석

### 1. 거래 빈도 차이 (-74%)

| 요인 | 프리셋 (adxdi) | 최적화 (adx) | 영향 |
|------|---------------|-------------|------|
| ADX 임계값 | 10 (낮음) | 18-25 (높음) | **진입 기회 감소** |
| Stochastic | 사용 (추가 신호) | 미사용 | **신호 수 감소** |
| Downtrend Filter | 사용 | 미사용 (MTF만) | 약간 영향 |
| entry_validity | 불명 | 57.6h (긴 대기) | **신호 만료 증가** |

**결론**: ADX 임계값 상승 + Stochastic 제거 = 거래수 74% 감소

---

### 2. 승률 차이 (+11.3%)

| 요인 | 영향 |
|------|------|
| 높은 ADX 임계값 (18-25) | 강한 추세만 진입 → 승률 향상 |
| 짧은 trail_dist (0.015) | 빠른 익절 → 승률 향상 |
| 낮은 거래수 (679) | 선별된 신호 → 승률 향상 |

**결론**: 보수적 필터링 → 높은 승률 but 낮은 빈도

---

### 3. MDD 차이 (+100%)

| 프리셋 | 최적화 | 차이 |
|--------|--------|------|
| 11.05% | 22-26% | **2배 증가** ⚠️ |

**원인**:
- `atr_mult`: 1.5 → 1.2 (손절폭 -20%)
- `trail_start_r`: 1.2 → 0.8 (트레일링 시작 -33%)
- 낮은 거래빈도 → 연속 손실 시 회복 어려움

**결론**: 공격적 손절 + 낮은 거래빈도 = MDD 증가

---

## 전략 타입별 신호 생성 차이

### adxdi (프리셋)

```python
# 신호 조건 (추정)
if adx > adx_min and \
   stoch < stoch_long_max and \
   di_plus > di_minus and \
   use_downtrend_filter:
    signal = "Long"
```

**특징**:
- ADX 10 이상이면 진입 가능 (낮은 임계값)
- Stochastic 50 미만이면 과매도 → 추가 신호
- 다중 필터 → 높은 거래빈도

---

### adx (최적화, AlphaX7Core)

```python
# core/strategy_core.py:742-745
if self.strategy_type == 'adx':
    signals = self._extract_all_signals_adx(
        df_pattern,
        pattern_tolerance,
        entry_validity_hours,
        adx_period,
        adx_threshold  # 18-25 (높음)
    )
```

**특징**:
- ADX 18-25 이상 필요 (높은 임계값)
- Stochastic 미사용
- W/M 패턴 기반 진입
- 단일 필터 → 낮은 거래빈도

---

## 비교 요약

| 항목 | adxdi (프리셋) | adx (최적화) | 권장 |
|------|---------------|-------------|------|
| **전략 복잡도** | 높음 (ADX+Stoch+DI) | 중간 (ADX+DI) | adxdi (다양성) |
| **거래 빈도** | 높음 (2572회) | 낮음 (679회) | adxdi (수익 기회) |
| **승률** | 중간 (78.8%) | 높음 (90.1%) | adx (안정성) |
| **MDD** | 낮음 (11%) | 높음 (22-26%) | **adxdi** ✅ |
| **Profit Factor** | 0 (오류) | 10.93 | adx (메트릭 정확) |
| **Sharpe Ratio** | 불명 | 24.45 | adx |

---

## 권장사항

### 1. 프리셋 재검증 필요

**이유**:
- `profit_factor: 0` → 계산 오류 의심
- 2026-01-13 생성 → 최신 코드와 불일치 가능성
- `grade: C` → 낮은 등급

**방법**:
```python
# 프리셋 파라미터로 재백테스트
from core.strategy_core import AlphaX7Core

strategy = AlphaX7Core(strategy_type='adx')
result = strategy.run_backtest(
    df=df_1h,
    params={
        'atr_mult': 1.5,
        'trail_start_r': 1.2,
        'trail_dist_r': 0.03,
        'entry_validity_hours': 48.0,
        'adx_period': 14,
        'adx_threshold': 10,  # adx_min
    }
)
```

---

### 2. 하이브리드 파라미터 테스트

**목표**: 거래빈도 ↑ + MDD ↓

**제안**:
```python
{
    'atr_mult': 1.5,           # 프리셋 (넓은 손절)
    'trail_start_r': 1.2,      # 프리셋
    'trail_dist_r': 0.03,      # 프리셋
    'entry_validity_hours': 48.0,  # 중간값
    'adx_period': 14,          # 표준
    'adx_threshold': 15,       # 중간값 (10 vs 18-25)
}
```

**기대 효과**:
- 거래수: 679 → 1200+ (중간)
- 승률: 90% → 85% (약간 하락)
- MDD: 22% → 15% (개선)

---

### 3. Coarse Grid 범위 조정

**문제**: 현재 Coarse Grid는 ADX 임계값이 높게 설정됨

```python
# core/optimizer.py:1824-1826 (현재)
if self.strategy_type == 'adx':
    coarse_grid['adx_period'] = [10, 14, 18]
    coarse_grid['adx_threshold'] = [18.0, 22.0, 25.0]  # ← 너무 높음
```

**권장 수정**:
```python
if self.strategy_type == 'adx':
    coarse_grid['adx_period'] = [10, 14, 18]
    coarse_grid['adx_threshold'] = [10.0, 18.0, 25.0]  # ← 프리셋 값 포함
```

**효과**:
- 낮은 임계값 탐색 → 거래빈도 증가
- 프리셋 영역 커버 → 재현 가능

---

## 결론

### 현재 상황

1. **프리셋 (adxdi)**: 레거시 전략, 높은 거래빈도, 낮은 MDD
2. **최적화 (adx)**: 신규 전략, 낮은 거래빈도, 높은 승률, 높은 MDD
3. **전략 타입 불일치**: 직접 비교 불가능

### 우선순위

1. **Coarse Grid 조정** - `adx_threshold` 범위 확대 (10~25)
2. **하이브리드 테스트** - 프리셋 + 최적화 파라미터 혼합
3. **프리셋 재검증** - Profit Factor 0 오류 수정

### 최종 권장 전략

**단기**: 현재 최적화 결과 사용 (Sharpe 24.45, 안정적)
**장기**: Coarse Grid 조정 후 재최적화 → 거래빈도 개선

---

**작성**: 2026-01-17
**버전**: v7.22.1
