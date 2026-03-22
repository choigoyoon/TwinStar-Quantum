# Coarse-to-Fine 최적화 가이드 (v7.28)

## 개요

Coarse-to-Fine 최적화는 2단계 파라미터 탐색 시스템으로, 효율적으로 최적 파라미터를 찾습니다.

```
Stage 1: Coarse Grid (넓은 범위, 512개 조합)
    ↓ 상위 5개 결과 선택
    ↓
Stage 2: Fine-Tuning (좁은 범위, ~1,575개 조합 × 5 영역)
    ↓
Result: 최적 파라미터
```

## 설치 및 요구사항

### Python 버전
- Python 3.12+

### 의존성
```bash
pandas>=2.1.0
numpy>=1.26.0
```

### 프로젝트 의존성
- `core/optimizer.py`: BacktestOptimizer 클래스
- `core/strategy_core.py`: AlphaX7Core 전략
- `core/data_manager.py`: BotDataManager
- `utils/metrics.py`: 메트릭 계산 (SSOT)
- `config/parameters.py`: PARAMETER_SENSITIVITY_WEIGHTS
- `config/constants/trading.py`: TOTAL_COST

## 빠른 시작

### 1. 스크립트 실행 (권장)

```bash
# 프로젝트 루트에서 실행
python tools/run_coarse_to_fine.py
```

**출력 예시**:
```
====================================================================================================
2단계 Coarse-to-Fine 백테스트 - v7.28
   비용: TOTAL_COST = 0.0002 (SSOT)
====================================================================================================

데이터 로딩...
OK 데이터:
   15분봉: 50,957개
   1시간봉: 12,740개 (2020년 이후)
   기간: 2020-01-01 ~ 2026-01-17
   일수: 2,209일

Stage 1: Coarse Grid
   전체 조합: 512개
   필터 제거: 162개 (31.6%)
   유효 조합: 350개
   파라미터: atr_mult, filter_tf, entry_validity_hours, trail_start_r, trail_dist_r
   진행: 350/350 (100%)

Stage 1 완료: 348개 결과

상위 5개:
  1. Sharpe=27.32, 승률=95.7%, MDD=0.8%, 거래=2192
  2. Sharpe=26.15, 승률=94.2%, MDD=1.1%, 거래=1856
  ...
```

### 2. 프로그래밍 방식

```python
from core.coarse_to_fine_optimizer import CoarseToFineOptimizer
from core.data_manager import BotDataManager
import pandas as pd

# 1. 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
dm.load_historical()

# 15분봉 → 1시간봉 리샘플링
df_15m = dm.df_entry_full.copy()
if 'timestamp' not in df_15m.columns:
    df_15m.reset_index(inplace=True)

df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
df_temp = df_15m.set_index('timestamp')

df = df_temp.resample('1h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

df.reset_index(inplace=True)
df = df[df['timestamp'] >= '2020-01-01'].copy()

# 2. 최적화 실행
optimizer = CoarseToFineOptimizer(df, strategy_type='macd')
result = optimizer.run(n_cores=8, save_csv=True)

# 3. 결과 확인
print(f"최적 파라미터: {result.best_params}")
print(f"Sharpe: {result.best_metrics['sharpe']:.2f}")
print(f"승률: {result.best_metrics['win_rate']:.1f}%")
print(f"MDD: {result.best_metrics['mdd']:.1f}%")
print(f"총 조합 수: {result.total_combinations}개")
print(f"소요 시간: {result.elapsed_seconds:.1f}초")

# 4. 상위 15개 결과
for i, r in enumerate(result.stage2_results[:15], 1):
    print(f"{i}. Sharpe={r.sharpe_ratio:.2f}, 승률={r.win_rate:.1f}%, MDD={abs(r.max_drawdown):.1f}%")
```

## Stage 1: Coarse Grid

### 범위 정의

```python
{
    'atr_mult': [0.9, 1.0, 1.1, 1.25],           # 손절 배수 (4개)
    'filter_tf': ['4h', '6h', '8h', '12h'],      # 필터 타임프레임 (4개)
    'entry_validity_hours': [48, 72],            # 진입 유효시간 (2개)
    'trail_start_r': [0.4, 0.6, 0.8, 1.0],       # 트레일링 시작 (4개)
    'trail_dist_r': [0.03, 0.05, 0.08, 0.1]      # 트레일링 간격 (4개)
}

# 조합 수: 4 × 4 × 2 × 4 × 4 = 512개
```

### 범위 근거

| 파라미터 | 범위 | 근거 |
|---------|------|------|
| `atr_mult` | 0.9-1.25 | 손절 배수 핵심 범위 |
| `filter_tf` | 4h-12h | 설계 범위 (추세 필터) |
| `entry_validity_hours` | 48-72h | 중장기 대기 (거래 빈도 0.2-0.5/일) |
| `trail_start_r` | 0.4-1.0 | 트레일링 시작 배수 |
| `trail_dist_r` | 0.03-0.1 | 트레일링 간격 (v7.26 최적값 0.03 포함) |

### 파라미터 검증

3가지 불조화 규칙으로 자동 필터링 (~30% 조합 제거):

1. **atr_mult × trail_start_r ∈ [0.5, 2.5]**
2. **filter_tf vs entry_validity_hours 조화**
   - `filter_tf='12h'` → `entry_validity_hours ≤ 24`
   - `filter_tf='1d'` → `entry_validity_hours ≤ 48`
3. **trail_start_r / trail_dist_r ∈ [3.0, 20.0]**

## Stage 2: Fine-Tuning

### 범위 생성 규칙

Stage 1의 상위 5개 결과를 중심으로 좁은 범위 탐색:

| 파라미터 | 범위 생성 규칙 | 포인트 수 |
|---------|--------------|----------|
| `filter_tf` | 중심값 ±2단계 (허용 목록 내) | ~5개 |
| `trail_start_r` | 중심값 ±30% | 9개 |
| `trail_dist_r` | 중심값 ±25% | 7개 |
| `atr_mult` | 중심값 ±15% | 5개 |
| `entry_validity_hours` | Stage 1 최적값 고정 | 1개 |

**조합 수**: ~5 × 9 × 7 × 5 × 1 = ~1,575개 (필터 전)

### 예시

Stage 1 최적 파라미터가 다음과 같다면:
```python
{
    'atr_mult': 1.0,
    'filter_tf': '6h',
    'entry_validity_hours': 48,
    'trail_start_r': 0.6,
    'trail_dist_r': 0.05
}
```

Stage 2 범위:
```python
{
    'atr_mult': [0.850, 0.925, 1.000, 1.075, 1.150],  # ±15%
    'filter_tf': ['4h', '6h', '8h', '12h'],           # ±2단계
    'entry_validity_hours': [48],                      # 고정
    'trail_start_r': [0.420, 0.465, 0.510, 0.555, 0.600, 0.645, 0.690, 0.735, 0.780],  # ±30%
    'trail_dist_r': [0.038, 0.041, 0.044, 0.047, 0.050, 0.053, 0.056, 0.059, 0.063]   # ±25%
}
```

## 결과 분석

### CoarseFineResult 구조

```python
@dataclass
class CoarseFineResult:
    stage1_results: List[OptimizationResult]  # Stage 1 전체 결과
    stage2_results: List[OptimizationResult]  # Stage 2 전체 결과
    best_params: dict                          # 최적 파라미터
    best_metrics: dict                         # 최적 메트릭
    total_combinations: int                    # 총 조합 수
    elapsed_seconds: float                     # 소요 시간
    csv_path: str | None = None                # CSV 저장 경로
```

### 메트릭 항목

```python
best_metrics = {
    'sharpe': 27.32,        # Sharpe Ratio
    'win_rate': 95.7,       # 승률 (%)
    'mdd': 0.8,             # MDD (%)
    'pnl': 826.8,           # 총 수익률 (%)
    'trades': 2192,         # 거래 횟수
    'pf': 26.68,            # Profit Factor
    'stability': 'S'        # 안정성 등급
}
```

### CSV 출력

파일명: `results/coarse_fine_results_YYYYMMDD_HHMMSS.csv`

컬럼:
- `sharpe`: Sharpe Ratio
- `win_rate`: 승률 (%)
- `mdd`: MDD (%)
- `pnl`: 총 수익률 (%)
- `trades`: 거래 횟수
- `pf`: Profit Factor
- `stability`: 안정성 등급
- `atr_mult`, `filter_tf`, `entry_validity_hours`, `trail_start_r`, `trail_dist_r`: 파라미터

## 성능 특성

| 항목 | 수치 | 설명 |
|------|------|------|
| **Stage 1 조합** | 512개 | 필터 후 ~350개 |
| **Stage 2 조합** | ~7,875개 | 1,575개 × 5 영역 |
| **총 조합** | ~8,225개 | Stage 1+2 합계 |
| **실행 시간** | 8-12분 | 8코어 기준 |
| **메모리** | ~500MB | DataFrame + Results |
| **CPU 부하** | 75-90% | 워커 8개 병렬 |

### 시스템 요구사항

| 구성 요소 | 최소 | 권장 |
|---------|------|------|
| CPU 코어 | 4코어 | 8코어 이상 |
| RAM | 4GB | 8GB 이상 |
| 디스크 | 1GB 여유 | 2GB 여유 |
| 실행 시간 | ~20분 | ~8분 |

## 고급 사용법

### 1. 커스텀 범위 정의

```python
class CustomCoarseToFineOptimizer(CoarseToFineOptimizer):
    def build_coarse_ranges(self):
        """커스텀 Coarse Grid 범위"""
        return {
            'atr_mult': [0.8, 1.0, 1.2, 1.5, 2.0],  # 더 넓은 범위
            'filter_tf': ['2h', '4h', '6h', '8h', '12h', '1d'],
            'entry_validity_hours': [24, 48, 72, 96],
            'trail_start_r': [0.3, 0.5, 0.7, 0.9, 1.2],
            'trail_dist_r': [0.02, 0.04, 0.06, 0.08, 0.1, 0.15]
        }

# 사용
optimizer = CustomCoarseToFineOptimizer(df, strategy_type='macd')
result = optimizer.run(n_cores=8)
```

### 2. 특정 영역만 Fine-Tuning

```python
# Stage 1만 실행
stage1_results = optimizer.run_stage_1(n_cores=8)

# 1등만 Fine-Tuning
top_1 = [stage1_results[0]]
stage2_results = optimizer.run_stage_2(top_1, n_cores=8)
```

### 3. 결과 필터링

```python
# Sharpe > 20, 승률 > 90% 결과만
filtered = [
    r for r in result.stage2_results
    if r.sharpe_ratio > 20 and r.win_rate > 90
]

print(f"필터링된 결과: {len(filtered)}개")
```

## 트러블슈팅

### 문제 1: 메모리 부족

**증상**: `MemoryError` 발생

**해결**:
```python
# DataFrame 크기 축소 (최근 5,000개만 사용)
df = df.tail(5000).reset_index(drop=True)

# 또는 워커 수 감소
result = optimizer.run(n_cores=4)
```

### 문제 2: 실행 시간 너무 긴

**증상**: 20분 이상 소요

**해결**:
```python
# Coarse Grid 범위 축소
def build_coarse_ranges(self):
    return {
        'atr_mult': [0.9, 1.0, 1.1],        # 4→3개
        'filter_tf': ['4h', '6h', '8h'],    # 4→3개
        # ... (조합 수: 512→216개)
    }

# 또는 상위 3개만 Fine-Tuning
stage2_results = optimizer.run_stage_2(top_3, n_cores=8)
```

### 문제 3: 모든 조합이 필터링됨

**증상**: `Stage 1 완료: 0개 결과`

**해결**:
```python
# 검증 규칙 완화
class RelaxedOptimizer(CoarseToFineOptimizer):
    def validate_param_interaction(self, params):
        # Rule 1만 체크
        interaction_1 = params['atr_mult'] * params['trail_start_r']
        return 0.3 <= interaction_1 <= 3.0  # 더 넓은 범위
```

## 참고 자료

- **CLAUDE.md**: 프로젝트 개발 규칙
- **core/optimizer.py**: BacktestOptimizer 기본 클래스
- **config/parameters.py**: PARAMETER_SENSITIVITY_WEIGHTS
- **utils/metrics.py**: 메트릭 계산 (SSOT)

## 버전 이력

- **v7.28** (2026-01-20): 최초 구현
  - 2단계 Coarse-to-Fine 최적화
  - 파라미터 검증 규칙 추가
  - CSV 저장 기능
  - 단위 테스트 7개 (100% 통과)

## 라이선스

TwinStar-Quantum 프로젝트 라이선스를 따릅니다.
