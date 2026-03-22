# TwinStar-Quantum 최적화 전략 가이드

> **버전**: 2.0.0
> **작성일**: 2026-01-15
> **대상**: 백테스트 최적화 사용자 (Quick/Standard/Deep 모드)

---

## 📖 목차

1. [개요](#1-개요)
2. [최적화 모드 비교](#2-최적화-모드-비교)
3. [전략별 파라미터 범위](#3-전략별-파라미터-범위)
   - [MACD 전략](#31-macd-전략)
   - [ADX+DI 전략](#32-adxdi-전략)
   - [WM Pattern 전략](#33-wm-pattern-전략)
4. [프리셋 타입별 목표 함수](#4-프리셋-타입별-목표-함수)
5. [실전 사용 가이드](#5-실전-사용-가이드)
6. [FAQ](#6-faq)

---

## 1. 개요

TwinStar-Quantum은 **3가지 최적화 모드**와 **3가지 거래 전략**을 지원합니다.

### 최적화 모드

| 모드 | 조합 수 | 예상 시간 | 용도 |
|------|--------|---------|------|
| **Quick** | 144~300개 | ~7분 | 빠른 검증 (개발/테스트) |
| **Standard** | 4,320~5,184개 | ~44분 | 실사용 권장 |
| **Deep** | 259,200~777,600개 | ~12시간 | 전수조사 (정밀 분석) |

### 거래 전략

| 전략 | 설명 | 주요 파라미터 |
|------|------|--------------|
| **MACD** | 이동평균 수렴/확산 지표 | macd_fast, macd_slow, macd_signal |
| **ADX+DI** | 추세 강도 + 방향성 지표 | adx_period, adx_threshold |
| **WM Pattern** | W/M 패턴 인식 전략 | pattern_tolerance, entry_validity_hours |

---

## 2. 최적화 모드 비교

### 2.1 Quick Mode (빠른 최적화)

#### 특징
- ⏱️ **예상 시간**: 7분
- 🔢 **조합 수**: 64~300개
- 🎯 **목표**: 빠른 검증 (개발 단계)
- 📊 **반환 결과**: 1개 (최적)

#### 그리드 설정
```python
{
    'filter_tf': ['4h', '6h'],              # 2개 (제한적)
    'entry_tf': ['15m'],                    # 1개 (고정)
    'leverage': [1, 3],                     # 2개 (낮음~중간)
    'direction': ['Both'],                  # 1개 (양방향 고정)

    'atr_mult': [2.0, 3.0],                 # 2개 (중간~높음)
    'trail_start_r': [1.5, 2.5],            # 2개 (중간~늦음)
    'trail_dist_r': [0.2]                   # 1개 (고정)
}
```

#### 권장 사용 시나리오
- ✅ 새로운 전략 아이디어 검증
- ✅ 파라미터 범위 확인
- ✅ 개발 중 빠른 테스트
- ❌ 실제 운영 환경 (Standard 권장)

---

### 2.2 Standard Mode (표준 최적화) ⭐ 권장

#### 특징
- ⏱️ **예상 시간**: 44분
- 🔢 **조합 수**: 4,320~5,184개
- 🎯 **목표**: 실사용 최적 파라미터 도출
- 📊 **반환 결과**: 3개 (🔥공격 / ⚖균형 / 🛡보수)

#### 그리드 설정
```python
{
    'filter_tf': ['4h', '6h', '12h'],       # 3개 (주요 타임프레임)
    'entry_tf': ['15m'],                    # 1개 (고정)
    'leverage': [1, 3, 5],                  # 3개 (전체 범위)
    'direction': ['Both', 'Long'],          # 2개 (양방향/롱)

    'atr_mult': [1.5, 2.0, 2.5, 3.0],       # 4개 (전체 범위)
    'trail_start_r': [1.0, 1.5, 2.0, 2.5],  # 4개 (전체 범위)
    'trail_dist_r': [0.15, 0.2, 0.3]        # 3개 (주요 값)
}
```

#### 권장 사용 시나리오
- ✅ **실제 운영 환경** (가장 권장)
- ✅ 프리셋 생성
- ✅ 승률 80% 목표
- ✅ 3가지 리스크 프로필 비교

---

### 2.3 Deep Mode (심층 최적화)

#### 특징
- ⏱️ **예상 시간**: 12시간
- 🔢 **조합 수**: 259,200~777,600개
- 🎯 **목표**: 전수조사 (최고 품질)
- 📊 **반환 결과**: 5개+ (🔥공격×3 / ⚖균형 / 🛡보수 / 🎯고승률 / 🐢저빈도)

#### 그리드 설정
```python
{
    'filter_tf': ['4h', '6h', '12h', '1d'], # 4개 (전체)
    'entry_tf': ['15m', '30m'],             # 2개 (진입 TF 비교)
    'leverage': [1, 2, 3, 5],               # 4개 (전체)
    'direction': ['Both', 'Long', 'Short'], # 3개 (전체)

    'atr_mult': [1.5, 2.0, 2.5, 3.0, 3.5],        # 5개 (확장)
    'trail_start_r': [0.8, 1.0, 1.5, 2.0, 2.5, 3.0], # 6개 (확장)
    'trail_dist_r': [0.15, 0.2, 0.25, 0.3, 0.4]    # 5개 (확장)
}
```

#### 권장 사용 시나리오
- ✅ 전략 최종 검증
- ✅ 연구/분석 목적
- ✅ 최고 품질 파라미터 필요
- ⚠️ 시간 여유 필요 (12시간+)
- ⚠️ 8GB+ 메모리 권장

---

## 3. 전략별 파라미터 범위

### 3.1 MACD 전략

#### 전략 개요

MACD(Moving Average Convergence Divergence)는 **이동평균선의 수렴/확산**을 이용한 추세 추종 지표입니다.

**주요 파라미터**:
- `macd_fast`: 빠른 EMA 기간 (기본값: 6)
- `macd_slow`: 느린 EMA 기간 (기본값: 18)
- `macd_signal`: 시그널 라인 기간 (기본값: 7)

---

#### Quick Mode - MACD

```json
{
  "strategy": "macd",
  "mode": "quick",
  "total_combinations": 144,
  "estimated_time": "7분",

  "parameters": {
    "macd_fast": [6, 8, 10],              // 3개 (민감도)
    "macd_slow": [18, 22, 26],            // 3개 (추세)
    "macd_signal": [7, 9],                // 2개 (시그널)

    "filter_tf": ["4h", "6h"],
    "entry_tf": ["15m"],
    "leverage": [1, 3],
    "direction": ["Both"],

    "atr_mult": [2.0, 3.0],
    "trail_start_r": [1.5, 2.5],
    "trail_dist_r": [0.2]
  }
}
```

**총 조합**: 3 × 3 × 2 × 2 × 1 × 2 × 1 × 2 × 2 × 1 = **144개**

---

#### Standard Mode - MACD ⭐

```json
{
  "strategy": "macd",
  "mode": "standard",
  "total_combinations": 28800,
  "top_results": 5184,
  "estimated_time": "44분",

  "parameters": {
    "macd_fast": [4, 6, 8, 10, 12],       // 5개 (전체 범위)
    "macd_slow": [16, 18, 22, 26, 30],    // 5개 (전체 범위)
    "macd_signal": [5, 7, 9, 11],         // 4개 (전체 범위)

    "filter_tf": ["4h", "6h", "12h"],
    "entry_tf": ["15m"],
    "leverage": [1, 3, 5],
    "direction": ["Both", "Long"],

    "atr_mult": [1.5, 2.0, 2.5, 3.0],
    "trail_start_r": [1.0, 1.5, 2.0, 2.5],
    "trail_dist_r": [0.15, 0.2, 0.3]
  }
}
```

**총 조합**: 5 × 5 × 4 × 3 × 1 × 3 × 2 × 4 × 4 × 3 = **28,800개**
**반환**: 상위 5,184개

---

#### Deep Mode - MACD

```json
{
  "strategy": "macd",
  "mode": "deep",
  "total_combinations": 259200,
  "estimated_time": "12시간",

  "parameters": {
    "macd_fast": [4, 5, 6, 8, 10, 12],     // 6개 (확장)
    "macd_slow": [16, 18, 20, 22, 26, 30], // 6개 (확장)
    "macd_signal": [5, 6, 7, 9, 11],       // 5개 (확장)

    "filter_tf": ["4h", "6h", "12h", "1d"],
    "entry_tf": ["15m", "30m"],
    "leverage": [1, 2, 3, 5],
    "direction": ["Both", "Long", "Short"],

    "atr_mult": [1.5, 2.0, 2.5, 3.0, 3.5],
    "trail_start_r": [0.8, 1.0, 1.5, 2.0, 2.5, 3.0],
    "trail_dist_r": [0.15, 0.2, 0.25, 0.3, 0.4]
  }
}
```

**총 조합**: 6 × 6 × 5 × 4 × 2 × 4 × 3 × 5 × 6 × 5 = **259,200개**

---

#### MACD 파라미터 영향도

| 파라미터 | 낮은 값 | 높은 값 | 권장 범위 |
|---------|--------|--------|----------|
| `macd_fast` | 민감 (잦은 신호) | 둔감 (적은 신호) | 4~12 |
| `macd_slow` | 빠른 추세 전환 | 느린 추세 전환 | 16~30 |
| `macd_signal` | 빠른 신호 | 지연된 신호 | 5~11 |

**최적화 팁**:
- 📈 **변동성 높은 시장**: `macd_fast=4~6`, `macd_signal=5~7` (민감)
- 📊 **안정적인 추세**: `macd_fast=10~12`, `macd_signal=9~11` (둔감)
- ⚖️ **균형잡힌 설정**: `macd_fast=6`, `macd_slow=18`, `macd_signal=7` (기본값)

---

### 3.2 ADX+DI 전략

#### 전략 개요

ADX(Average Directional Index)는 **추세의 강도**를 측정하며, DI(Directional Indicator)는 **추세의 방향**을 나타냅니다.

**주요 파라미터**:
- `adx_period`: ADX 계산 기간 (기본값: 14)
- `adx_threshold`: 추세 강도 임계값 (기본값: 25.0)
- `enable_adx_filter`: ADX 필터 활성화 여부

**ADX 해석**:
- `ADX < 20`: 약한 추세 (범위 시장)
- `ADX 20~25`: 약한 추세 형성 중
- `ADX 25~50`: 강한 추세
- `ADX > 50`: 매우 강한 추세

---

#### Quick Mode - ADX

```json
{
  "strategy": "adx",
  "mode": "quick",
  "total_combinations": 64,
  "estimated_time": "7분",

  "parameters": {
    "adx_period": [14, 18],               // 2개 (표준/느림)
    "adx_threshold": [20.0, 25.0],        // 2개 (약함/중간)
    "enable_adx_filter": [true],          // 1개 (필터 활성화)

    "filter_tf": ["4h", "6h"],
    "entry_tf": ["15m"],
    "leverage": [1, 3],
    "direction": ["Both"],

    "atr_mult": [2.0, 3.0],
    "trail_start_r": [1.5, 2.5],
    "trail_dist_r": [0.2]
  }
}
```

**총 조합**: 2 × 2 × 1 × 2 × 1 × 2 × 1 × 2 × 2 × 1 = **64개**

---

#### Standard Mode - ADX ⭐

```json
{
  "strategy": "adx",
  "mode": "standard",
  "total_combinations": 25920,
  "top_results": 4320,
  "estimated_time": "44분",

  "parameters": {
    "adx_period": [10, 12, 14, 18, 21],    // 5개 (전체 범위)
    "adx_threshold": [20.0, 25.0, 30.0],   // 3개 (약함/중간/강함)
    "enable_adx_filter": [true, false],    // 2개 (on/off)

    "filter_tf": ["4h", "6h", "12h"],
    "entry_tf": ["15m"],
    "leverage": [1, 3, 5],
    "direction": ["Both", "Long"],

    "atr_mult": [1.5, 2.0, 2.5, 3.0],
    "trail_start_r": [1.0, 1.5, 2.0, 2.5],
    "trail_dist_r": [0.15, 0.2, 0.3]
  }
}
```

**총 조합**: 5 × 3 × 2 × 3 × 1 × 3 × 2 × 4 × 4 × 3 = **25,920개**
**반환**: 상위 4,320개

---

#### Deep Mode - ADX

```json
{
  "strategy": "adx",
  "mode": "deep",
  "total_combinations": 432000,
  "estimated_time": "12시간",

  "parameters": {
    "adx_period": [10, 12, 14, 16, 18, 21], // 6개 (확장)
    "adx_threshold": [15.0, 20.0, 25.0, 30.0, 35.0], // 5개 (확장)
    "enable_adx_filter": [true, false],     // 2개

    "filter_tf": ["4h", "6h", "12h", "1d"],
    "entry_tf": ["15m", "30m"],
    "leverage": [1, 2, 3, 5],
    "direction": ["Both", "Long", "Short"],

    "atr_mult": [1.5, 2.0, 2.5, 3.0, 3.5],
    "trail_start_r": [0.8, 1.0, 1.5, 2.0, 2.5, 3.0],
    "trail_dist_r": [0.15, 0.2, 0.25, 0.3, 0.4]
  }
}
```

**총 조합**: 6 × 5 × 2 × 4 × 2 × 4 × 3 × 5 × 6 × 5 = **432,000개**

---

#### ADX 파라미터 영향도

| 파라미터 | 낮은 값 | 높은 값 | 권장 범위 |
|---------|--------|--------|----------|
| `adx_period` | 민감 (빠른 반응) | 둔감 (느린 반응) | 10~21 |
| `adx_threshold` | 약한 추세도 포함 | 강한 추세만 필터 | 15~35 |
| `enable_adx_filter` | 필터 없음 (모든 신호) | 강한 추세만 거래 | true/false |

**최적화 팁**:
- 📈 **강한 추세 시장**: `adx_threshold=25~30`, `enable_adx_filter=true`
- 📊 **범위 시장**: `adx_threshold=15~20` (약한 추세 포함)
- ⚠️ **과최적화 주의**: ADX 필터 on/off 비교 필수

---

### 3.3 WM Pattern 전략

#### 전략 개요

WM Pattern 전략은 **W자형(상승 반전)** 및 **M자형(하락 반전)** 패턴을 인식하여 진입하는 패턴 트레이딩 전략입니다.

**주요 파라미터**:
- `pattern_tolerance`: 패턴 인식 오차 범위 (기본값: 0.05 = 5%)
- `entry_validity_hours`: 패턴 유효 시간 (기본값: 6.0시간)
- `max_adds`: 최대 추가 매매 횟수 (기본값: 1)

---

#### Quick Mode - WM Pattern

```json
{
  "strategy": "wm_pattern",
  "mode": "quick",
  "total_combinations": 64,
  "estimated_time": "7분",

  "parameters": {
    "pattern_tolerance": [0.04, 0.05],     // 2개 (엄격/표준)
    "entry_validity_hours": [24.0, 48.0],  // 2개 (1일/2일)
    "max_adds": [1],                       // 1개 (고정)

    "filter_tf": ["4h", "6h"],
    "entry_tf": ["15m"],
    "leverage": [1, 3],
    "direction": ["Both"],

    "atr_mult": [2.0, 3.0],
    "trail_start_r": [1.5, 2.5],
    "trail_dist_r": [0.2]
  }
}
```

**총 조합**: 2 × 2 × 1 × 2 × 1 × 2 × 1 × 2 × 2 × 1 = **64개**

---

#### Standard Mode - WM Pattern ⭐

```json
{
  "strategy": "wm_pattern",
  "mode": "standard",
  "total_combinations": 27648,
  "top_results": 4320,
  "estimated_time": "44분",

  "parameters": {
    "pattern_tolerance": [0.02, 0.03, 0.04, 0.05], // 4개
    "entry_validity_hours": [12.0, 24.0, 48.0, 72.0], // 4개
    "max_adds": [1, 2],                    // 2개 (추가 매매)

    "filter_tf": ["4h", "6h", "12h"],
    "entry_tf": ["15m"],
    "leverage": [1, 3, 5],
    "direction": ["Both", "Long"],

    "atr_mult": [1.5, 2.0, 2.5, 3.0],
    "trail_start_r": [1.0, 1.5, 2.0, 2.5],
    "trail_dist_r": [0.15, 0.2, 0.3]
  }
}
```

**총 조합**: 4 × 4 × 2 × 3 × 1 × 3 × 2 × 4 × 4 × 3 = **27,648개**
**반환**: 상위 4,320개

---

#### Deep Mode - WM Pattern

```json
{
  "strategy": "wm_pattern",
  "mode": "deep",
  "total_combinations": 777600,
  "estimated_time": "12시간",

  "parameters": {
    "pattern_tolerance": [0.02, 0.03, 0.04, 0.05, 0.06, 0.08], // 6개
    "entry_validity_hours": [12.0, 24.0, 36.0, 48.0, 60.0, 72.0], // 6개
    "max_adds": [0, 1, 2],                 // 3개 (추가 없음~2회)

    "filter_tf": ["4h", "6h", "12h", "1d"],
    "entry_tf": ["15m", "30m"],
    "leverage": [1, 2, 3, 5],
    "direction": ["Both", "Long", "Short"],

    "atr_mult": [1.5, 2.0, 2.5, 3.0, 3.5],
    "trail_start_r": [0.8, 1.0, 1.5, 2.0, 2.5, 3.0],
    "trail_dist_r": [0.15, 0.2, 0.25, 0.3, 0.4]
  }
}
```

**총 조합**: 6 × 6 × 3 × 4 × 2 × 4 × 3 × 5 × 6 × 5 = **777,600개**

---

#### WM Pattern 파라미터 영향도

| 파라미터 | 낮은 값 | 높은 값 | 권장 범위 |
|---------|--------|--------|----------|
| `pattern_tolerance` | 엄격한 패턴 (적은 신호) | 관대한 패턴 (많은 신호) | 0.02~0.08 |
| `entry_validity_hours` | 신속한 진입 | 오래 대기 | 12~72시간 |
| `max_adds` | 단순 거래 | 복합 매매 | 0~2 |

**최적화 팁**:
- 📈 **고빈도 매매**: `pattern_tolerance=0.05~0.08`, `entry_validity_hours=12~24`
- 📊 **신중한 진입**: `pattern_tolerance=0.02~0.03`, `entry_validity_hours=48~72`
- ⚠️ **추가 매매 주의**: `max_adds=0` (단순) vs `max_adds=2` (복합) 비교 필수

---

## 4. 프리셋 타입별 목표 함수

### 4.1 Conservative (보수형) 프리셋 🛡️

#### 목표
```python
objective = "minimize(MDD) + maximize(Sharpe Ratio)"
```

#### 등급 기준

| 등급 | MDD | Sharpe Ratio | 승률 |
|------|-----|-------------|------|
| 🏆 S | ≤ 5% | ≥ 1.5 | - |
| 🥇 A | ≤ 7.5% | ≥ 1.3 | - |
| 🥈 B | ≤ 10% | ≥ 1.0 | - |
| 🥉 C | > 10% | < 1.0 | - |

#### 권장 파라미터

```python
conservative_params = {
    'atr_mult': 3.0~3.5,         # 높은 SL (안전)
    'trail_start_r': 2.0~2.5,    # 늦은 트레일링
    'trail_dist_r': 0.15~0.2,    # 좁은 트레일링 거리

    'leverage': 1~2,             # 낮은 레버리지
    'direction': 'Both',         # 양방향 (기회 확보)
    'filter_tf': '6h' or '12h',  # 큰 타임프레임
}
```

#### 실전 예시

```json
{
  "name": "보수형 MACD (실적 검증)",
  "strategy": "macd",
  "results": {
    "mdd": 3.73,
    "sharpe_ratio": 1.61,
    "win_rate": 79.99,
    "grade": "S"
  },
  "params": {
    "macd_fast": 6,
    "macd_slow": 18,
    "macd_signal": 7,
    "atr_mult": 3.5,
    "trail_start_r": 2.0,
    "leverage": 1
  }
}
```

---

### 4.2 Balanced (균형형) 프리셋 ⚖️

#### 목표
```python
objective = "maximize(Sharpe Ratio) with MDD ≤ 15%"
```

#### 등급 기준

| 등급 | Sharpe Ratio | MDD |
|------|-------------|-----|
| 🏆 S | ≥ 1.2 | ≤ 15% |
| 🥇 A | ≥ 1.0 | ≤ 20% |
| 🥈 B | ≥ 0.8 | ≤ 25% |
| 🥉 C | < 0.8 | > 25% |

#### 권장 파라미터

```python
balanced_params = {
    'atr_mult': 2.0~2.5,         # 중간 SL
    'trail_start_r': 1.5~2.0,    # 중간 트레일링
    'trail_dist_r': 0.2~0.3,     # 중간 트레일링 거리

    'leverage': 2~3,             # 중간 레버리지
    'direction': 'Both',         # 양방향
    'filter_tf': '4h' or '6h',   # 중간 타임프레임
}
```

#### 실전 예시

```json
{
  "name": "균형형 MACD (실적 검증)",
  "strategy": "macd",
  "results": {
    "sharpe_ratio": 1.38,
    "mdd": 9.71,
    "win_rate": 75.12,
    "grade": "S"
  },
  "params": {
    "macd_fast": 8,
    "macd_slow": 22,
    "macd_signal": 9,
    "atr_mult": 2.5,
    "trail_start_r": 1.5,
    "leverage": 3
  }
}
```

---

### 4.3 Aggressive (공격형) 프리셋 🔥

#### 목표
```python
objective = "maximize(Total Return) with MDD ≤ 40%"
```

#### 등급 기준

| 등급 | CAGR | MDD |
|------|------|-----|
| 🏆 S | ≥ 100% | ≤ 40% |
| 🥇 A | ≥ 50% | ≤ 50% |
| 🥈 B | ≥ 30% | ≤ 60% |
| 🥉 C | < 30% | > 60% |

#### 권장 파라미터

```python
aggressive_params = {
    'atr_mult': 1.5~2.0,         # 낮은 SL (공격)
    'trail_start_r': 0.8~1.5,    # 빠른 트레일링
    'trail_dist_r': 0.3~0.4,     # 넓은 트레일링 거리

    'leverage': 3~5,             # 높은 레버리지
    'direction': 'Both',         # 양방향 (기회 극대화)
    'filter_tf': '4h',           # 작은 타임프레임 (빠른 신호)
}
```

#### 실전 예시

```json
{
  "name": "공격형 MACD (실적 검증)",
  "strategy": "macd",
  "results": {
    "compound_return": 628234.9,
    "mdd": 33.06,
    "win_rate": 68.45,
    "grade": "S"
  },
  "params": {
    "macd_fast": 4,
    "macd_slow": 16,
    "macd_signal": 5,
    "atr_mult": 1.5,
    "trail_start_r": 0.8,
    "leverage": 5
  }
}
```

---

## 5. 실전 사용 가이드

### 5.1 최적화 실행 순서

#### 1️⃣ Quick Mode로 범위 확인 (7분)

```python
# GUI에서:
# 1. Optimization 탭 클릭
# 2. Mode: "Quick" 선택
# 3. Strategy: "MACD" 선택
# 4. Exchange: "bybit", Symbol: "BTCUSDT"
# 5. Run Optimization 클릭

# 결과 확인:
# - 1개 결과 반환 (최적)
# - 파라미터 범위가 적절한지 확인
# - MDD, Sharpe, Win Rate 확인
```

#### 2️⃣ Standard Mode로 실사용 파라미터 도출 (44분) ⭐

```python
# GUI에서:
# 1. Mode: "Standard" 선택
# 2. 동일한 설정 유지
# 3. Run Optimization 클릭

# 결과 확인:
# - 3개 결과 반환 (🔥공격/⚖균형/🛡보수)
# - 각 프리셋 타입별 등급 확인
# - 프리셋으로 저장 (Save Preset 버튼)
```

#### 3️⃣ Deep Mode로 정밀 분석 (12시간, 선택)

```python
# 시간 여유가 있을 때만 실행
# - 5개+ 결과 반환
# - 고승률형, 저빈도형 포함
# - 최종 검증용
```

---

### 5.2 결과 분석 방법

#### A. 등급 해석

```
🏆 S등급: 목표 초과달성 (실전 즉시 사용 가능)
🥇 A등급: 목표 달성 (실전 사용 권장)
🥈 B등급: 준수한 성과 (실전 사용 가능, 관찰 필요)
🥉 C등급: 미흡 (추가 최적화 필요)
❌ D/F등급: 부적합 (사용 지양)
```

#### B. 주요 지표 체크리스트 (v2.2 - 강화된 기준)

```python
✅ 필수 확인 항목 (필터링 조건):
1. MDD ≤ 20% (절대 조건, 강화됨)
2. Win Rate ≥ 75% (승률, 강화됨)
3. 최소 거래수 ≥ 10 (통계적 유의성)
4. 다중 코어 병렬 처리 (자동 활성화)

⚠️ 추가 확인 항목:
5. Sharpe Ratio ≥ 1.0 (위험 대비 수익)
6. Profit Factor ≥ 1.5 (수익 팩터)
7. 매매 빈도 0.5~2회/일 (적절성)
8. 3구간 안정성 ✅ (균형)
```

#### C. 필터링 조건 (v2.2)

**최적화 엔진에서 자동 적용되는 필터**:

```python
# core/optimizer.py (라인 682-686)
passes_filter = (
    abs(result.max_drawdown) <= 20.0 and  # MDD ≤ 20%
    result.win_rate >= 75.0 and           # 승률 ≥ 75%
    result.trades >= 10                   # 최소 거래수 ≥ 10
)
```

이 조건을 통과하지 못한 결과는 **자동으로 제외**됩니다.

#### C. 프리셋 선택 가이드

```python
if risk_tolerance == 'low':
    # 보수형 선택 (MDD ≤ 5%)
    preset_type = 'conservative'

elif risk_tolerance == 'medium':
    # 균형형 선택 (Sharpe ≥ 1.2)
    preset_type = 'balanced'

else:
    # 공격형 선택 (CAGR ≥ 100%)
    preset_type = 'aggressive'
```

---

### 5.3 프리셋 저장 및 로드

#### 프리셋 저장

```python
# GUI에서:
# 1. 최적화 결과 테이블에서 원하는 결과 선택
# 2. "Save Preset" 버튼 클릭
# 3. 프리셋 이름 입력 (예: "bybit_btc_macd_conservative")
# 4. 확인

# 저장 위치:
# config/presets/{preset_name}.json
```

#### 프리셋 로드

```python
# 백테스트 탭에서:
# 1. Preset 드롭다운 메뉴 클릭
# 2. 저장된 프리셋 선택
# 3. 파라미터 자동 반영
# 4. Run Backtest 클릭
```

---

### 5.4 모드별 권장 시나리오

| 시나리오 | 권장 모드 | 이유 |
|---------|---------|------|
| 새로운 전략 테스트 | Quick | 빠른 검증 (7분) |
| 실제 운영 환경 설정 | Standard | 3가지 리스크 프로필 제공 |
| 전략 최종 검증 | Deep | 최고 품질, 다양한 옵션 |
| 프리셋 생성 | Standard | 실사용 권장 |
| 연구/분석 목적 | Deep | 전수조사 |

---

## 6. FAQ

### Q1. Quick과 Standard의 차이는?

**A**: 탐색 범위와 반환 결과 개수입니다.

- **Quick**: 144개 조합, 1개 결과 (7분)
- **Standard**: 5,184개 조합, 3개 결과 (44분) ← **권장**

Standard 모드는 🔥공격/⚖균형/🛡보수 3가지 프리셋을 제공하여 실전 사용에 적합합니다.

---

### Q2. Deep Mode는 언제 사용하나요?

**A**: 다음 경우에 사용하세요.

1. **전략 최종 검증**: 실전 투입 전 마지막 검증
2. **연구/분석**: 학술적 목적
3. **최고 품질 필요**: 시간이 충분할 때

⚠️ **주의**: 12시간 소요, 8GB+ 메모리 권장

---

### Q3. 프리셋 타입을 어떻게 선택하나요?

**A**: 위험 감수 성향에 따라 선택하세요.

```python
if risk_tolerance == 'low':
    preset = 'conservative'  # 🛡️ MDD ≤ 5%, Sharpe ≥ 1.5

elif risk_tolerance == 'medium':
    preset = 'balanced'      # ⚖️ Sharpe ≥ 1.2, MDD ≤ 15%

else:
    preset = 'aggressive'    # 🔥 CAGR ≥ 100%, MDD ≤ 40%
```

---

### Q4. 등급이 C 이하인 경우 어떻게 하나요?

**A**: 다음 방법을 시도하세요.

1. **다른 전략 시도**: MACD → ADX 또는 WM Pattern
2. **타임프레임 변경**: 1h → 4h 또는 1d
3. **심볼 변경**: BTCUSDT → ETHUSDT
4. **Deep Mode 실행**: 더 넓은 범위 탐색

---

### Q5. 최적화 결과를 어떻게 검증하나요?

**A**: 다음 체크리스트를 확인하세요.

```python
✅ 1. MDD ≤ 25% (절대 조건)
✅ 2. 최소 거래수 ≥ 10
✅ 3. Sharpe Ratio ≥ 1.0
✅ 4. Win Rate ≥ 70%
✅ 5. 3구간 안정성 ✅
✅ 6. 매매 빈도 적절 (0.5~2회/일)
```

추가로, **백테스트 탭**에서 프리셋을 로드하여 다른 기간/심볼로 재검증하세요.

---

### Q6. MACD vs ADX vs WM Pattern 중 어떤 전략이 좋나요?

**A**: 시장 상황에 따라 다릅니다.

| 전략 | 적합한 시장 | 특징 |
|------|-----------|------|
| **MACD** | 추세 시장 | 이동평균 수렴/확산, 범용성 높음 |
| **ADX+DI** | 강한 추세 시장 | 추세 강도 필터, 신뢰도 높음 |
| **WM Pattern** | 반전 시장 | W/M 패턴 인식, 고승률 |

**권장**: 3가지 전략 모두 Standard Mode로 최적화한 후 비교

---

### Q7. 최적화 결과가 과최적화(Overfitting)된 건 아닌가요?

**A**: 다음 방법으로 검증하세요.

1. **다른 기간 테스트**: 2023년 데이터 → 2024년 데이터로 재검증
2. **다른 심볼 테스트**: BTCUSDT → ETHUSDT 또는 SOLUSDT
3. **Out-of-Sample 검증**: 최적화 기간 외 데이터로 테스트
4. **3구간 안정성 확인**: ✅ 표시된 결과 선택

**과최적화 징후**:
- Win Rate > 95% (비현실적)
- Sharpe Ratio > 5.0 (과도하게 높음)
- 거래수 < 10 (통계적 무의미)

---

### Q8. 최적화 중 중단하고 싶어요.

**A**: GUI에서 "Cancel" 버튼을 클릭하세요.

- 이미 완료된 결과는 유지됩니다.
- 부분 결과도 확인 가능합니다.

---

### Q9. 메모리 부족 오류가 발생했어요.

**A**: 다음 방법을 시도하세요.

1. **Deep Mode → Standard Mode** 변경
2. **다른 프로그램 종료** (Chrome, VSCode 등)
3. **코어 수 감소**: 설정에서 CPU 코어 수 조정 (4 → 2)
4. **메모리 증설**: 최소 8GB 권장

---

### Q10. 프리셋 파일을 공유하고 싶어요.

**A**: `config/presets/{name}.json` 파일을 복사하여 공유하세요.

```json
{
  "_meta": {
    "name": "bybit_btc_macd_conservative",
    "symbol": "BTCUSDT",
    "exchange": "bybit",
    "strategy": "macd",
    "version": "2.0.0"
  },
  "params": {
    "macd_fast": 6,
    "macd_slow": 18,
    ...
  }
}
```

다른 사용자는 이 파일을 `config/presets/`에 복사 후 GUI에서 로드하면 됩니다.

---

## 📚 참고 문서

- [PRESET_GUIDE.md](PRESET_GUIDE.md) - 프리셋 사용 가이드
- [PARAMETER_IMPACT_GUIDE.md](PARAMETER_IMPACT_GUIDE.md) - 파라미터 영향도 분석
- [OPTIMIZATION_REPORT.md](../OPTIMIZATION_REPORT.md) - Phase 1-C 최적화 완료 보고서

---

## 📌 버전 정보

- **문서 버전**: 2.0.0
- **작성일**: 2026-01-15
- **작성자**: Claude Opus 4.5
- **프로젝트**: TwinStar-Quantum

---

**🎯 요약**:

1. **Quick Mode (7분)**: 빠른 검증용
2. **Standard Mode (44분)**: 실사용 권장 ⭐
3. **Deep Mode (12시간)**: 최고 품질

각 모드는 **3가지 전략**(MACD/ADX/WM)과 **3가지 프리셋**(보수/균형/공격)을 지원하며, 프리셋별 등급 기준으로 평가됩니다.

**실전 사용**: Standard Mode로 최적화 → 프리셋 저장 → 백테스트로 재검증
