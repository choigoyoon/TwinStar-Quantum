# TwinStar-Quantum 전략 전체 분석 가이드

> **작성일**: 2026-01-16  
> **버전**: v3.0 (완전 분석)  
> **목적**: MACD/ADX 전략, WM 인식 과정, TF 필터, 프리셋 파라미터 영향도 완전 정리

---

## 목차
1. [전체 아키텍처](#1-전체-아키텍처)
2. [TF 3개 필터 시스템](#2-tf-3개-필터-시스템)
3. [WM 패턴 인식 과정](#3-wm-패턴-인식-과정-상세)
4. [MACD 전략 상세](#4-macd-전략-상세)
5. [ADX 전략 상세](#5-adx-전략-상세)
6. [프리셋 파라미터 영향도](#6-프리셋-파라미터-영향도)
7. [현재 저장된 프리셋 비교](#7-현재-저장된-프리셋-비교)

---

## 1. 전체 아키텍처

### 1.1 신호 생성 흐름

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TwinStar-Quantum 신호 파이프라인                       │
└─────────────────────────────────────────────────────────────────────────────┘

[데이터 입력]                    [지표 계산]                     [패턴 인식]
┌──────────────┐              ┌──────────────┐              ┌──────────────┐
│  df_1h       │──────────────│    MACD      │──────────────│  H/L 포인트  │
│  (1시간봉)    │              │ fast/slow/   │              │   추출       │
└──────────────┘              │   signal     │              └──────┬───────┘
      │                       └──────────────┘                     │
      │                                                           ▼
┌──────────────┐              ┌──────────────┐              ┌──────────────┐
│  df_15m      │──────────────│    RSI       │              │  W/M 패턴    │
│  (15분봉)    │              │  (period)    │              │   탐지       │
└──────────────┘              └──────────────┘              └──────┬───────┘
      │                                                           │
      │                       ┌──────────────┐                    │
      │                       │    ATR       │◄───────────────────┤
      │                       │  (period)    │                    │
      │                       └──────────────┘                    │
      │                                                           ▼
      │                       ┌──────────────┐              ┌──────────────┐
      │                       │    ADX       │─────────────►│   필터링     │
      │                       │  (period/    │              │  (5단계)     │
      │                       │   threshold) │              └──────┬───────┘
      │                       └──────────────┘                     │
      │                                                           ▼
      │                       ┌──────────────┐              ┌──────────────┐
      └──────────────────────►│  MTF 필터    │─────────────►│   신호 출력   │
        (trend 계산용)         │ (EMA 기반)   │              │ Long/Short   │
                              └──────────────┘              └──────────────┘
```

### 1.2 핵심 파일 구조

| 파일 | 역할 | 주요 함수/클래스 |
|------|------|-----------------|
| `core/strategy_core.py` | 전략 엔진 | `AlphaX7Core`, `detect_signal()` |
| `config/parameters.py` | 파라미터 SSOT | `DEFAULT_PARAMS`, `PARAM_RANGES` |
| `utils/indicators.py` | 지표 계산 | `calculate_rsi()`, `calculate_atr()`, `calculate_adx()`, `calculate_macd()` |
| `core/optimization_logic.py` | 최적화 엔진 | `FILTER_CRITERIA`, `passes_filter()` |
| `config/presets/*.json` | 프리셋 저장 | MACD/ADX 전략별 최적값 |

---

## 2. TF 3개 필터 시스템

### 2.1 타임프레임 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TF 3개 필터 시스템                                 │
└─────────────────────────────────────────────────────────────────────────────┘

  [filter_tf]          [trend_interval]         [entry_tf]
  상위 추세 필터         기준 타임프레임            진입 타임프레임
      │                      │                       │
      ▼                      ▼                       ▼
  ┌────────┐            ┌────────┐              ┌────────┐
  │  4h    │            │   1h   │              │  15m   │
  │  6h    │            │        │              │        │
  │  12h   │            │        │              │        │
  │  1d    │            │        │              │        │
  └────────┘            └────────┘              └────────┘
      │                      │                       │
      ▼                      ▼                       ▼
  MTF 추세              MACD 계산               ATR/RSI/
  (EMA 기반)            H/L 포인트              진입가격
      │                      │                       │
      └──────────┬───────────┴───────────┬──────────┘
                 │                       │
                 ▼                       ▼
           추세 방향 확인            패턴 + 진입점
           (up/down)                  결정
```

### 2.2 TF별 역할

| TF | 파라미터명 | 기본값 | 역할 | 영향 |
|----|-----------|-------|------|------|
| **filter_tf** | `filter_tf` | `4h` | MTF 추세 필터 | 승률↑, 거래수↓ |
| **trend_interval** | `trend_interval` | `1h` | MACD 계산 기준 | 패턴 정확도 |
| **entry_tf** | `entry_tf` | `15m` | 진입 시점 결정 | ATR/RSI 계산 |

### 2.3 MTF 필터 로직 (get_mtf_trend)

```python
# 위치: core/strategy_core.py (라인 281-333)
def get_mtf_trend(self, df_base, mtf=None, entry_tf=None, ema_period=20):
    """
    1. df_base (1h 데이터)를 mtf (4h/1d 등)로 리샘플링
    2. EMA(10) 계산
    3. 현재가 > EMA → 'up' (Long 허용)
    4. 현재가 < EMA → 'down' (Short 허용)
    """
    # 자동 MTF 결정 (entry_tf → MTF_MAP)
    MTF_MAP = {'15m': '4h', '1h': 'D'}
    
    # 리샘플링 후 EMA 비교
    ema_val = ACTIVE_PARAMS.get('ema_period', 10)
    ema = df_final['close'].ewm(span=ema_val, adjust=False).mean()
    
    return 'up' if last_close > last_ema else 'down'
```

### 2.4 filter_tf 값별 영향

| filter_tf | 예상 효과 | 승률 | 거래수/일 | MDD |
|-----------|----------|------|----------|-----|
| `2h` | 필터 약함 | ~62% | 2.2회 | ~17% |
| `4h` | 기본값 | ~75% | 1.5회 | ~15% |
| `6h` | 중간 | ~80% | 1.0회 | ~12% |
| `12h` | 강함 | ~82% | 0.5회 | ~10% |
| `1d` | 매우 강함 | ~85%+ | 0.3회 | ~8% |

---

## 3. WM 패턴 인식 과정 (상세)

### 3.1 전체 흐름도

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WM 패턴 인식 6단계 프로세스                             │
└─────────────────────────────────────────────────────────────────────────────┘

    STEP 1               STEP 2               STEP 3
  MACD 계산          히스토그램 분석        H/L 포인트 추출
┌───────────┐      ┌───────────┐      ┌───────────┐
│  Fast EMA │      │ hist > 0  │      │    H      │
│  (6일)    │──────│ ────────► │──────│  (고점)   │
│  Slow EMA │      │ hist < 0  │      │    L      │
│  (18일)   │      │ ────────► │      │  (저점)   │
└───────────┘      └───────────┘      └───────────┘
      │                  │                  │
      ▼                  ▼                  ▼
    STEP 4               STEP 5               STEP 6
  패턴 매칭            필터 검증            신호 생성
┌───────────┐      ┌───────────┐      ┌───────────┐
│ W: L-H-L  │      │ Tolerance │      │  Long @   │
│ (더블바텀) │──────│ Validity  │──────│  W 패턴   │
│ M: H-L-H  │      │ MTF/ADX   │      │  Short @  │
│ (더블탑)  │      │           │      │  M 패턴   │
└───────────┘      └───────────┘      └───────────┘
```

### 3.2 STEP 1: MACD 계산

```python
# 위치: core/strategy_core.py (라인 429-434)

# 기본 파라미터 (config/parameters.py)
macd_fast = 6     # 단기 EMA (기본 12 → 최적화 6)
macd_slow = 18    # 장기 EMA (기본 26 → 최적화 18)
macd_signal = 7   # 시그널 라인 (기본 9 → 최적화 7)

# MACD 계산
exp1 = df_1h['close'].ewm(span=macd_fast, adjust=False).mean()  # Fast EMA
exp2 = df_1h['close'].ewm(span=macd_slow, adjust=False).mean()  # Slow EMA
macd = exp1 - exp2                                               # MACD Line
signal_line = macd.ewm(span=macd_signal, adjust=False).mean()    # Signal
hist = macd - signal_line                                        # Histogram
```

**MACD 파라미터 영향:**

| 파라미터 | 값 범위 | 작으면 | 크면 |
|---------|--------|-------|------|
| `macd_fast` | 4-12 | 민감(신호↑) | 둔감(신호↓) |
| `macd_slow` | 16-30 | 빠른 반응 | 안정적 |
| `macd_signal` | 5-11 | 빠른 신호 | 지연된 신호 |

### 3.3 STEP 2-3: 히스토그램 분석 → H/L 포인트 추출

```python
# 위치: core/strategy_core.py (라인 436-471)

points = []  # H/L 포인트 저장

while i < n:
    if hist.iloc[i] > 0:  # 양수 구간 (상승세)
        # 구간 내 최고점(H) 추출
        seg = df_1h.iloc[start:i]
        max_idx = seg['high'].idxmax()
        points.append({
            'type': 'H',               # High 포인트
            'price': df_1h.loc[max_idx, 'high'],
            'time': df_1h.loc[max_idx, 'timestamp'],
            'confirmed_time': df_1h.iloc[i-1]['timestamp']
        })
        
    elif hist.iloc[i] < 0:  # 음수 구간 (하락세)
        # 구간 내 최저점(L) 추출
        seg = df_1h.iloc[start:i]
        min_idx = seg['low'].idxmin()
        points.append({
            'type': 'L',               # Low 포인트
            'price': df_1h.loc[min_idx, 'low'],
            ...
        })
```

**히스토그램 구간 분석:**
```
                  H (고점)
                  │
    hist > 0     │     hist > 0
    (양수 구간)   │    (양수 구간)
         ┌──────┐│┌──────┐
         │      │││      │
    ─────┤      ├┼┤      ├─────  0 기준선
         │      │││      │
         └──────┘│└──────┘
                 │
    hist < 0     │    hist < 0
    (음수 구간)   │   (음수 구간)
                 │
                 L (저점)
```

### 3.4 STEP 4: 패턴 매칭 (W/M)

```python
# 위치: core/strategy_core.py (라인 473-534)

# W 패턴 (Long 신호) - 더블 바텀
# L(저점1) → H(고점) → L(저점2) 순서로 패턴 완성
if (points[i]['type'] == 'L' and 
    points[i+1]['type'] == 'H' and 
    points[i+2]['type'] == 'L'):
    
    L1, H, L2 = points[i], points[i+1], points[i+2]
    # L1과 L2의 가격 차이가 tolerance 이내면 W 패턴!

# M 패턴 (Short 신호) - 더블 탑
# H(고점1) → L(저점) → H(고점2) 순서로 패턴 완성
if (points[i]['type'] == 'H' and 
    points[i+1]['type'] == 'L' and 
    points[i+2]['type'] == 'H'):
    
    H1, L, H2 = points[i], points[i+1], points[i+2]
    # H1과 H2의 가격 차이가 tolerance 이내면 M 패턴!
```

**패턴 시각화:**
```
W 패턴 (Long 진입)          M 패턴 (Short 진입)
                                    H1      H2
       H                            ┌┐      ┌┐
      ┌┐                            ││      ││
      ││                            │└──────┘│
      │└──────┐                     │   L    │
      │       │                     │        │
   L1─┘       └─L2               ───┘        └───
   
   L2 ≈ L1 (tolerance 이내)      H2 ≈ H1 (tolerance 이내)
```

### 3.5 STEP 5: 5단계 필터 검증

```python
# 패턴이 발견되면 5단계 필터를 통과해야 신호 생성

# 필터 1: Tolerance (가격 편차)
diff = abs(L2['price'] - L1['price']) / L1['price']
if diff >= pattern_tolerance:  # 기본 5%
    continue  # 필터링 - 패턴 무효

# 필터 2: Entry Validity (유효 시간)
hours_since = (last_time - confirmed_time) / 3600
if hours_since > entry_validity_hours:  # 기본 6시간
    continue  # 필터링 - 패턴 만료

# 필터 3: MTF Filter (상위 TF 추세)
if self.USE_MTF_FILTER and trend_val != 'up':  # Long인 경우
    continue  # 필터링 - 추세 불일치

# 필터 4: ADX Filter (추세 강도) - 선택적
if enable_adx_filter:
    adx_value = self.calculate_adx(df_1h, period=14)
    if adx_value < adx_threshold:  # 기본 25
        continue  # 필터링 - 추세 약함

# 필터 5: ATR 유효성
atr = self.calculate_atr(df_15m, period=14)
if atr is None or atr <= 0:
    continue  # 필터링 - ATR 무효
```

### 3.6 STEP 6: 신호 생성

```python
# 모든 필터 통과 → 신호 생성

# 진입가격 (15분봉 현재가)
price = df_15m.iloc[-1]['close']

# 손절가 계산 (ATR 기반)
atr_mult = adaptive_params.get('atr_mult', 1.25)
sl = price - atr * atr_mult  # Long의 경우
# sl = price + atr * atr_mult  # Short의 경우

# 신호 반환
return TradeSignal(
    signal_type='Long',  # 또는 'Short'
    pattern='W',         # 또는 'M'
    stop_loss=sl,
    atr=atr,
    timestamp=datetime.now()
)
```

---

## 4. MACD 전략 상세

### 4.1 파라미터 정의

```python
# 위치: config/parameters.py

DEFAULT_PARAMS = {
    # MACD 파라미터 (최적화됨)
    'macd_fast': 6,      # [OPT] 12 → 6 (매우 민감)
    'macd_slow': 18,     # [OPT] 26 → 18 (빠름)
    'macd_signal': 7,    # [OPT] 9 → 7 (민감)
}

PARAM_RANGES = {
    # MACD 최적화 범위 (start, end, step)
    'macd_fast': (4, 12, 2),    # 4, 6, 8, 10, 12
    'macd_slow': (16, 30, 2),   # 16, 18, 20, 22, 24, 26, 28, 30
    'macd_signal': (5, 11, 2),  # 5, 7, 9, 11
}
```

### 4.2 MACD 계산 공식

```
MACD Line = EMA(close, fast) - EMA(close, slow)
Signal Line = EMA(MACD, signal)
Histogram = MACD Line - Signal Line
```

### 4.3 현재 저장된 MACD 프리셋

**파일**: `config/presets/bybit_btcusdt_1h_macd.json`

```json
{
  "_meta": {
    "symbol": "BTCUSDT",
    "exchange": "bybit",
    "timeframe": "1h",
    "strategy": "macd",
    "version": "2.0.0"
  },
  "_result": {
    "trades": 2216,
    "win_rate": 83.75,
    "simple_pnl": 2077.05,
    "max_drawdown": 10.86,
    "profit_factor": 5.06,
    "grade": "A"
  },
  "params": {
    "atr_mult": 1.5,
    "trail_start": 1.2,
    "trail_dist": 0.03,
    "tolerance": 0.1,
    "adx_min": 10,
    "use_downtrend_filter": true
  }
}
```

### 4.4 MACD 파라미터 → 결과 영향도

| 파라미터 | 값 변화 | 승률 영향 | MDD 영향 | 거래수 영향 |
|---------|--------|---------|---------|----------|
| macd_fast ↓ | 6→4 | ↓ | ↑ | ↑ (신호 과다) |
| macd_fast ↑ | 6→12 | ↑ | ↓ | ↓ (신호 감소) |
| macd_slow ↓ | 18→16 | ↓ | ↑ | ↑ |
| macd_slow ↑ | 18→30 | ↑ | ↓ | ↓ |
| macd_signal ↓ | 7→5 | ↓ | ↑ | ↑ |
| macd_signal ↑ | 7→11 | ↑ | ↓ | ↓ |

---

## 5. ADX 전략 상세

### 5.1 ADX 파라미터 정의

```python
# 위치: config/parameters.py

DEFAULT_PARAMS = {
    # ADX 파라미터 (Session 8 추가)
    'adx_period': 14,          # ADX 계산 기간 (표준)
    'adx_threshold': 25.0,     # 추세 강도 임계값 (>25: 강한 추세)
    'enable_adx_filter': False, # ADX 필터 활성화 여부 (기본 비활성)
}

PARAM_RANGES = {
    # ADX 최적화 범위
    'adx_period': (10, 21, 1),
    'adx_threshold': (20.0, 30.0, 5.0),
}
```

### 5.2 ADX 계산 공식 (Wilder's Smoothing)

```python
# 위치: utils/indicators.py (라인 244-361)

# 1. +DM (Positive Directional Movement)
if high_diff > low_diff and high_diff > 0:
    plus_dm = high_diff

# 2. -DM (Negative Directional Movement)  
if low_diff > high_diff and low_diff > 0:
    minus_dm = low_diff

# 3. True Range (ATR과 동일)
TR = max(H-L, |H-Pc|, |L-Pc|)

# 4. Wilder's Smoothing (지수이동평균)
smoothed[i] = smoothed[i-1] - (smoothed[i-1] / period) + data[i]

# 5. +DI / -DI 계산
+DI = 100 × (+DM_smooth / ATR_smooth)
-DI = 100 × (-DM_smooth / ATR_smooth)

# 6. DX (Directional Index)
DX = 100 × |+DI - -DI| / (+DI + -DI)

# 7. ADX (DX의 Wilder's Smoothing)
ADX = Wilder_Smooth(DX, period)
```

### 5.3 ADX 값 해석

| ADX 값 | 추세 강도 | 매매 전략 |
|-------|----------|---------|
| 0-25 | 약한 추세 | 레인지 전략 (진입 자제) |
| 25-50 | 강한 추세 | **추세 추종 추천** |
| 50-75 | 매우 강한 추세 | 적극 진입 |
| 75-100 | 극도로 강한 추세 | 과매수/과매도 주의 |

### 5.4 ADX 필터 적용 로직

```python
# 위치: core/strategy_core.py (라인 414-420)

if enable_adx_filter:
    adx_value = self.calculate_adx(df_1h_safe, period=adx_period)
    if adx_value < adx_threshold:
        # ADX < 25 → 추세 약함 → 신호 무시
        logger.debug(f"❌ ADX filter: {adx_value:.1f} < {adx_threshold}")
        return None
    logger.debug(f"✅ ADX filter passed: {adx_value:.1f} >= {adx_threshold}")
```

### 5.5 현재 저장된 ADX 프리셋

**파일**: `config/presets/bybit_btcusdt_1h_adxdi.json`

```json
{
  "_meta": {
    "symbol": "BTCUSDT",
    "exchange": "bybit",
    "timeframe": "1h",
    "strategy": "adxdi",
    "version": "2.0.0"
  },
  "_result": {
    "trades": 2572,
    "win_rate": 78.81,
    "simple_pnl": 1938.05,
    "max_drawdown": 11.05,
    "profit_factor": 0,
    "grade": "C"
  },
  "params": {
    "atr_mult": 1.5,
    "trail_start": 1.2,
    "trail_dist": 0.03,
    "tolerance": 0.1,
    "adx_min": 10,
    "use_downtrend_filter": true
  }
}
```

### 5.6 ADX 파라미터 → 결과 영향도

| 파라미터 | 값 변화 | 승률 영향 | MDD 영향 | 거래수 영향 |
|---------|--------|---------|---------|----------|
| adx_period ↓ | 14→10 | ↓ | ↑ | ↑ (민감) |
| adx_period ↑ | 14→21 | ↑ | ↓ | ↓ (둔감) |
| adx_threshold ↓ | 25→20 | ↓ | ↑ | ↑ |
| adx_threshold ↑ | 25→30 | ↑ | ↓ | ↓↓ |

---

## 6. 프리셋 파라미터 영향도

### 6.1 전체 파라미터 분류

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          프리셋 파라미터 분류                                 │
└─────────────────────────────────────────────────────────────────────────────┘

[지표 파라미터]            [리스크 파라미터]           [패턴 파라미터]
├─ macd_fast              ├─ atr_mult               ├─ pattern_tolerance
├─ macd_slow              ├─ trail_start_r         ├─ entry_validity_hours
├─ macd_signal            ├─ trail_dist_r          └─ max_adds
├─ ema_period             └─ leverage
├─ rsi_period
├─ atr_period             [타임프레임]               [비용]
├─ adx_period             ├─ filter_tf             ├─ slippage
└─ adx_threshold          ├─ entry_tf              └─ fee
                          └─ direction
```

### 6.2 파라미터별 결과 영향 매트릭스

| 파라미터 | 승률 | MDD | 거래수 | 수익률 | 중요도 |
|---------|------|-----|-------|-------|-------|
| **filter_tf** | +++↑ | ++↓ | +++↓ | + | ⭐⭐⭐⭐⭐ |
| **leverage** | - | +++↑ | - | +++↑ | ⭐⭐⭐⭐ |
| **atr_mult** | ++↑ | +↓ | +↓ | + | ⭐⭐⭐⭐ |
| **entry_validity_hours** | +↑ | +↓ | ++↓ | + | ⭐⭐⭐ |
| **macd_fast** | +↑ | +↓ | +↓ | + | ⭐⭐⭐ |
| **trail_start_r** | +↑ | +↓ | - | +↑ | ⭐⭐⭐ |
| **adx_threshold** | ++↑ | +↓ | ++↓ | + | ⭐⭐⭐ |
| **pattern_tolerance** | +↑ | +↓ | +↓ | + | ⭐⭐ |

### 6.3 주요 파라미터 상세 영향

#### 6.3.1 filter_tf (가장 중요)

```
┌─────────────────────────────────────────────────┐
│              filter_tf 영향도                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  2h ──────────────────────────────────► 1d     │
│  약한 필터                           강한 필터   │
│                                                 │
│  승률:   62% ───────────────────────► 85%+     │
│  거래수: 2.2회/일 ──────────────────► 0.3회/일  │
│  MDD:   17% ────────────────────────► 8%       │
│                                                 │
└─────────────────────────────────────────────────┘
```

#### 6.3.2 leverage (리스크 조절)

```
레버리지   MDD(1x 기준)   실제 MDD
  1x         5.7%         5.7%
  3x         5.7%        17.1%
  5x         5.7%        28.5%
 10x         5.7%        57.0%
 
⚠️ 목표 MDD 20% 이내 유지 권장
   → 레버리지 = 20% / (1x MDD)
   → 예: 1x MDD 5.7% → 최대 3.5x 권장
```

#### 6.3.3 atr_mult (손절 폭)

```
atr_mult ↓ (1.0)            atr_mult ↑ (3.0)
┌───────────────┐          ┌───────────────┐
│ 좁은 SL       │          │ 넓은 SL       │
│ 빈번한 손절   │    vs    │ 적은 손절     │
│ 승률 낮음     │          │ 승률 높음     │
│ 손실폭 작음   │          │ 손실폭 큼     │
└───────────────┘          └───────────────┘

권장: 1.25 ~ 2.0 (적응형 사용 권장)
```

#### 6.3.4 entry_validity_hours (패턴 유효시간)

```
6h (기본)                   48~96h (권장)
┌───────────────┐          ┌───────────────┐
│ 신선한 패턴   │          │ 검증된 패턴   │
│ 많은 거래     │    vs    │ 적은 거래     │
│ 노이즈 포함   │          │ 신뢰성 높음   │
└───────────────┘          └───────────────┘

목표 0.5회/일 달성 → 48h+ 권장
```

---

## 7. 현재 저장된 프리셋 비교

### 7.1 프리셋 목록

| 프리셋명 | 전략 | 승률 | MDD | PF | 등급 |
|---------|------|------|-----|-----|-----|
| bybit_btcusdt_1h_macd | MACD | 83.75% | 10.86% | 5.06 | **A** |
| bybit_btcusdt_1h_adxdi | ADX-DI | 78.81% | 11.05% | 0.00 | C |
| gui_optimized_preset | MACD | 75.00% | 13.38% | 3.21 | A |
| bybit_BTCUSDT_15min | MACD | 72.50% | 12.30% | 2.10 | A |
| bybit_btcusdt_1h_75 | - | 75.50% | 15.00% | - | A |

### 7.2 MACD vs ADX 비교

| 항목 | MACD | ADX-DI |
|------|------|--------|
| 승률 | 83.75% ✅ | 78.81% |
| MDD | 10.86% ✅ | 11.05% |
| 거래수 | 2,216 | 2,572 |
| PF | 5.06 ✅ | 0.00 |
| 등급 | A ✅ | C |

**결론**: MACD 전략이 ADX-DI보다 전반적으로 우수

### 7.3 최적화 필터 기준

```python
# 위치: core/optimization_logic.py

FILTER_CRITERIA = {
    'max_mdd': 20.0,          # MDD ≤ 20%
    'min_win_rate': 70.0,     # 승률 ≥ 70%
    'min_pf': 1.5,            # PF ≥ 1.5
    'min_trades_per_day': 0.33,  # 3일에 1회 이상
}

GRADE_CRITERIA = {
    'S': {'win_rate': 85, 'mdd': 12, 'pf': 3.0},
    'A': {'win_rate': 75, 'mdd': 17, 'pf': 2.0},
    'B': {'win_rate': 70, 'mdd': 20, 'pf': 1.5},
    'C': '나머지'
}
```

---

## 8. 요약 및 권장사항

### 8.1 현재 상태

- **MACD 프리셋**: 승률 83.75%, MDD 10.86% → **양호** ✅
- **ADX 프리셋**: 승률 78.81%, MDD 11.05% → 개선 필요
- **공통 문제**: 거래수 1.0~1.2회/일 → 목표 0.5회/일

### 8.2 권장 변경사항

```python
# Before (현재)
filter_tf = '4h'
entry_validity_hours = 6.0

# After (권장)
filter_tf = '12h'  # 또는 '1d'
entry_validity_hours = 48.0  # 또는 72.0

# 기대 효과
# - 승률: 83% → 85%+
# - MDD: 유지
# - 거래수: 1.0회/일 → 0.3~0.5회/일
```

### 8.3 다음 단계

1. filter_tf를 12h 또는 1d로 변경하여 재최적화
2. entry_validity_hours를 48~96h로 확대
3. ADX 전략 파라미터 재검토 (PF 0 원인 분석)
4. 레버리지 조정 (목표 MDD 20% 기준)

---

> **작성**: AI Assistant (Claude)  
> **버전**: v3.0 완전 분석  
> **마지막 업데이트**: 2026-01-16
