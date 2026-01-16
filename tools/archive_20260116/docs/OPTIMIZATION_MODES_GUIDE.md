# 🎯 최적화 모드별 계산 방법 가이드

**버전**: v7.17
**마지막 업데이트**: 2026-01-16
**관련 파일**:
- [config/parameters.py](config/parameters.py) - `PARAM_RANGES_BY_MODE`
- [core/optimizer.py](core/optimizer.py) - `generate_grid_by_mode()`
- [ui/widgets/optimization/single.py](ui/widgets/optimization/single.py) - `_on_mode_changed()`

---

## 📊 개요

TwinStar Quantum은 **3가지 최적화 모드**를 제공합니다:
1. **Quick** - 빠른 탐색 (2-3분)
2. **Standard** - 균형잡힌 탐색 (5-10분)
3. **Deep** - 완전 탐색 (30-60분)

각 모드는 **파라미터 범위**를 자동으로 조정하여 조합 수를 제어합니다.

---

## 🔢 모드별 파라미터 범위 (PARAM_RANGES_BY_MODE)

### 위치: `config/parameters.py`

```python
PARAM_RANGES_BY_MODE = {
    # 필터 타임프레임 (문자열 리스트)
    'filter_tf': {
        'quick': ['12h', '1d'],              # 2개 - 문서 권장 (긴 TF)
        'standard': ['4h', '6h', '12h'],      # 3개
        'deep': ['2h', '4h', '6h', '12h', '1d']  # 5개 - 전체 범위
    },

    # 진입 유효시간 (시간 단위)
    'entry_validity_hours': {
        'quick': [48, 72],                    # 2개 - 문서 권장 (48~96h)
        'standard': [6, 12, 24, 48, 72],      # 5개 - 기본값 6.0 포함
        'deep': [6, 12, 24, 36, 48, 72, 96]   # 7개 - 96h 추가
    },

    # ATR 배수 (손절 거리)
    'atr_mult': {
        'quick': [1.25, 2.0],                 # 2개 - DEFAULT_PARAMS 포함
        'standard': [1.25, 1.5, 2.0, 2.5],    # 4개
        'deep': [1.0, 1.25, 1.5, 2.0, 2.5, 3.0]  # 6개
    },

    # 트레일링 시작 배수
    'trail_start_r': {
        'quick': [1.0, 1.5],                  # 2개
        'standard': [1.0, 1.5, 2.0, 2.5],     # 4개
        'deep': [0.8, 1.0, 1.5, 2.0, 2.5, 3.0]  # 6개
    },

    # 트레일링 간격
    'trail_dist_r': {
        'quick': [0.2],                       # 1개
        'standard': [0.2, 0.3],               # 2개
        'deep': [0.15, 0.2, 0.25, 0.3]        # 4개
    },
}
```

---

## 🧮 조합 수 계산 공식

각 모드의 **총 조합 수**는 다음과 같이 계산됩니다:

```
총 조합 수 = filter_tf × entry_validity_hours × atr_mult × trail_start_r × trail_dist_r
```

### Quick 모드

```
2 (filter_tf) × 2 (entry_validity) × 2 (atr_mult) × 2 (trail_start_r) × 1 (trail_dist_r)
= 8개
```

### Standard 모드

```
3 (filter_tf) × 5 (entry_validity) × 4 (atr_mult) × 4 (trail_start_r) × 2 (trail_dist_r)
= 60개
```

### Deep 모드

```
5 (filter_tf) × 7 (entry_validity) × 6 (atr_mult) × 6 (trail_start_r) × 4 (trail_dist_r)
= 1,080개
```

---

## 📋 모드별 상세 비교

| 항목 | Quick | Standard | Deep |
|------|-------|----------|------|
| **조합 수** | 8개 | 60개 | 1,080개 |
| **예상 시간** | 2-3분 | 5-10분 | 30-60분 |
| **권장 워커** | 4개 | 8개 | 16개 |
| **CPU 사용률** | 50% | 100% | 100% |
| **목표** | 빠른 검증 | 균형 탐색 | 완전 탐색 |
| **적합 상황** | 프리셋 검증 | 일반 최적화 | 정밀 최적화 |

---

## 💻 사용 방법

### 1. 파라미터 범위 조회

```python
from config.parameters import get_param_range_by_mode

# Quick 모드의 filter_tf 범위
filter_tf_quick = get_param_range_by_mode('filter_tf', 'quick')
# → ['12h', '1d']

# Deep 모드의 entry_validity_hours 범위
entry_validity_deep = get_param_range_by_mode('entry_validity_hours', 'deep')
# → [6, 12, 24, 36, 48, 72, 96]
```

### 2. 그리드 생성

```python
from core.optimizer import generate_grid_by_mode

# Standard 모드 그리드 생성
grid = generate_grid_by_mode(
    trend_tf='1h',
    mode='standard',
    max_mdd=20.0
)

print(f"filter_tf: {grid['filter_tf']}")  # ['4h', '6h', '12h']
print(f"atr_mult: {grid['atr_mult']}")    # [1.25, 1.5, 2.0, 2.5]
```

### 3. 조합 수 추정

```python
from core.optimizer import estimate_combinations

grid = generate_grid_by_mode('1h', 'standard')
combo_count, estimated_time_min = estimate_combinations(grid)

print(f"예상 조합 수: {combo_count}개")      # ~60개
print(f"예상 시간: {estimated_time_min}분")  # ~7분
```

### 4. UI에서 사용 (자동)

GUI에서 최적화 모드를 선택하면 자동으로 파라미터 범위가 설정됩니다:

```python
# ui/widgets/optimization/single.py

def _on_mode_changed(self, index: int):
    """모드 변경 시 자동 설정"""
    mode = MODE_MAP.get(index, 'standard')  # 0=Quick, 1=Standard, 2=Deep

    # 1. 파라미터 범위 가져오기
    ranges = get_indicator_range(mode)

    # 2. UI 위젯 업데이트
    self.atr_mult_widget.set_values(
        min(ranges['atr_mult']),
        max(ranges['atr_mult']),
        step
    )

    # 3. 예상 조합 수 표시
    combo_count, estimated_time = estimate_combinations(grid)
    self.estimated_combo_label.setText(f"예상 조합 수: ~{combo_count:,}개")
    self.estimated_time_label.setText(f"예상 시간: {estimated_time:.1f}분")
```

---

## 🎯 모드 선택 가이드

### Quick 모드 (8개, 2-3분)

**사용 시기**:
- 프리셋 검증
- 빠른 파라미터 테스트
- 문서 권장값 확인

**특징**:
- filter_tf: 12h, 1d (긴 타임프레임)
- entry_validity: 48h, 72h (긴 대기)
- 승률 85%+ 목표

**예제**:
```python
# Quick 모드로 문서 권장값 검증
optimizer = BacktestOptimizer(...)
grid = generate_grid_by_mode('1h', 'quick')
results = optimizer.grid_search(grid)
```

### Standard 모드 (60개, 5-10분)

**사용 시기**:
- 일반 최적화 작업
- 균형잡힌 탐색
- 일상적인 파라미터 조정

**특징**:
- filter_tf: 4h, 6h, 12h (기본값 포함)
- entry_validity: 6~72h (전 범위)
- 승률 75-85% 목표

**예제**:
```python
# Standard 모드로 균형 탐색
optimizer = BacktestOptimizer(...)
grid = generate_grid_by_mode('1h', 'standard')
results = optimizer.grid_search(grid)
```

### Deep 모드 (1,080개, 30-60분)

**사용 시기**:
- 정밀 최적화
- 전수 조사
- 새로운 전략 발굴

**특징**:
- filter_tf: 2h~1d (전체 범위)
- entry_validity: 6~96h (최대 범위)
- 승률 70-90% 목표

**주의**: CPU 집약적, 워커 8개 기준 약 4.5시간 소요

**예제**:
```python
# Deep 모드로 완전 탐색
optimizer = BacktestOptimizer(...)
grid = generate_grid_by_mode('1h', 'deep')
results = optimizer.grid_search(grid, max_workers=16)
```

---

## 📊 파라미터 영향도 순위

| 순위 | 파라미터 | 영향도 | Quick | Standard | Deep |
|------|----------|--------|-------|----------|------|
| 1 | `filter_tf` | ★★★★★ | 2개 | 3개 | 5개 |
| 2 | `entry_validity_hours` | ★★★★★ | 2개 | 5개 | 7개 |
| 3 | `trail_start_r` | ★★★★☆ | 2개 | 4개 | 6개 |
| 4 | `atr_mult` | ★★★★☆ | 2개 | 4개 | 6개 |
| 5 | `trail_dist_r` | ★★★☆☆ | 1개 | 2개 | 4개 |

**핵심 조합**: `filter_tf` + `entry_validity_hours`
- Quick: 2×2 = 4개 (승률 85%+ 목표)
- Standard: 3×5 = 15개 (균형)
- Deep: 5×7 = 35개 (완전 탐색)

---

## 🔧 고급 설정

### use_indicator_ranges 옵션

`generate_grid_by_mode()`에서 `use_indicator_ranges=True`로 설정하면 추가 지표 범위를 병합할 수 있습니다:

```python
grid = generate_grid_by_mode(
    trend_tf='1h',
    mode='deep',
    use_indicator_ranges=True  # 추가 지표 범위 병합
)

# grid에 rsi_period, macd_fast 등 추가 파라미터 포함
```

**주의**: `use_indicator_ranges=True`는 조합 수를 크게 증가시킵니다 (중복 주의).

### 워커 수 조정

CPU 코어 수에 따라 워커 수를 조정합니다:

```python
from core.optimizer import get_worker_info

# 모드별 권장 워커 정보
worker_info = get_worker_info('standard')
print(worker_info)
# → {'workers': 8, 'usage_percent': 100, 'max_workers': 16}

# 최적화 실행
results = optimizer.grid_search(grid, max_workers=worker_info['workers'])
```

---

## 📝 예제: 전체 워크플로우

```python
from core.optimizer import BacktestOptimizer, generate_grid_by_mode, estimate_combinations
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager

# 1. 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT')
dm.load_historical()

# 2. 옵티마이저 초기화
optimizer = BacktestOptimizer(
    strategy_class=AlphaX7Core,
    df=dm.df_entry_full
)

# 3. 모드 선택 및 그리드 생성
mode = 'standard'  # or 'quick', 'deep'
grid = generate_grid_by_mode('1h', mode)

# 4. 조합 수 추정
combo_count, estimated_time = estimate_combinations(grid)
print(f"예상 조합 수: {combo_count}개")
print(f"예상 시간: {estimated_time}분")

# 5. 최적화 실행
results = optimizer.grid_search(
    grid,
    slippage=0.0005,
    fee=0.0005,
    max_workers=8
)

# 6. 결과 확인
top_result = results[0]
print(f"최적 조합:")
print(f"  승률: {top_result.win_rate:.2f}%")
print(f"  MDD: {top_result.max_drawdown:.2f}%")
print(f"  PF: {top_result.profit_factor:.2f}")
print(f"  파라미터: {top_result.params}")
```

---

## 🚀 성능 최적화 팁

### 1. 모드 선택
- **빠른 검증**: Quick 모드 (2-3분)
- **일반 사용**: Standard 모드 (5-10분)
- **정밀 탐색**: Deep 모드 (30-60분) - CPU 여유 있을 때만

### 2. 워커 수 최적화
```python
import multiprocessing

cpu_count = multiprocessing.cpu_count()

# CPU 코어 수에 따라 워커 조정
if cpu_count >= 16:
    max_workers = 16  # Deep 모드 가능
elif cpu_count >= 8:
    max_workers = 8   # Standard 권장
else:
    max_workers = 4   # Quick 권장
```

### 3. 점진적 탐색
```python
# 1단계: Quick 모드로 빠른 탐색
quick_grid = generate_grid_by_mode('1h', 'quick')
quick_results = optimizer.grid_search(quick_grid)

# 2단계: Quick 결과를 바탕으로 Standard 범위 조정
best_filter_tf = quick_results[0].params['filter_tf']

# 3단계: Standard 모드로 정밀 조정
standard_grid = generate_grid_by_mode('1h', 'standard')
standard_grid['filter_tf'] = [best_filter_tf]  # 최적 filter_tf만 사용
standard_results = optimizer.grid_search(standard_grid)
```

---

## ⚠️ 주의 사항

### 1. Deep 모드 사용 시
- CPU 사용률 100% (장시간)
- 배터리 소모 주의
- 노트북의 경우 전원 연결 권장

### 2. 메모리 사용
- 조합 수가 많을수록 메모리 사용 증가
- Deep 모드는 약 2-4GB 메모리 필요

### 3. 과적합 방지
- Out-of-Sample 테스트 필수
- 훈련: 80%, 테스트: 20%

```python
# 데이터 분할
split_idx = int(len(df) * 0.8)
train_df = df.iloc[:split_idx]
test_df = df.iloc[split_idx:]

# 훈련 데이터로 최적화
optimizer_train = BacktestOptimizer(..., df=train_df)
results = optimizer_train.grid_search(grid)

# 테스트 데이터로 검증
optimizer_test = BacktestOptimizer(..., df=test_df)
test_result = optimizer_test._run_single(results[0].params)
```

---

## 📚 참고 자료

### 관련 파일
- [config/parameters.py](config/parameters.py) - 파라미터 범위 정의
- [core/optimizer.py](core/optimizer.py) - 최적화 엔진
- [ui/widgets/optimization/single.py](ui/widgets/optimization/single.py) - UI 구현

### 문서
- [CLAUDE.md](CLAUDE.md) - 프로젝트 규칙 (v7.17)
- [OPTIMIZATION_FINAL_SUMMARY_20260116.md](OPTIMIZATION_FINAL_SUMMARY_20260116.md) - 최적화 결과

### 예제
- [tools/optimize_leverage_range.py](tools/optimize_leverage_range.py) - 레버리지 최적화 예제

---

## ✅ 체크리스트

최적화 실행 전 확인:
- [ ] 모드 선택 (Quick/Standard/Deep)
- [ ] CPU 코어 수 확인 (워커 조정)
- [ ] 데이터 로드 완료 (Parquet 파일)
- [ ] 예상 시간 확인 (estimate_combinations)
- [ ] Out-of-Sample 데이터 준비 (20%)

---

**작성**: Claude Sonnet 4.5
**문서 버전**: 1.0
**마지막 업데이트**: 2026-01-16
**기반 버전**: v7.17 (CLAUDE.md)
