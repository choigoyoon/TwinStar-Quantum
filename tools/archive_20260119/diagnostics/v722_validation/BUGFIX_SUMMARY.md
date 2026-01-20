# v7.22 검증 테스트 버그 수정 요약

## 🐛 발견된 문제 (6개)

### 1. **META_PARAM_RANGES 불일치** (5개 테스트 실패)

**원인**: 테스트 코드가 실제 `config/meta_ranges.py`의 값과 다름

**수정 내역**:

| 파라미터 | 테스트 값 (잘못됨) | 실제 값 (올바름) | 파일 |
|----------|-------------------|-----------------|------|
| `trail_start_r` | 1.2 | 1.5 | test_optimal_params_validation.py |
| `trail_dist_r` (최소) | 0.005 | 0.01 | test_optimal_params_validation.py |
| `trail_dist_r` (최대) | 0.05 | 0.3 | test_optimal_params_validation.py |
| `trail_dist_r` (범위 밖) | 0.1 | 0.5 | test_optimal_params_validation.py |

**실제 META_PARAM_RANGES** (from `config/meta_ranges.py`):
```python
META_PARAM_RANGES = {
    'atr_mult': [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
    'filter_tf': ['2h', '4h', '6h', '12h', '1d'],
    'trail_start_r': [0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0],  # 1.2 없음!
    'trail_dist_r': [0.01, 0.015, 0.02, 0.025, 0.03, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3],
    'entry_validity_hours': [6, 12, 24, 36, 48, 72, 96]
}
```

---

### 2. **Coarse Grid 생성 로직 검증 오류** (1개 테스트 실패)

**문제**: `test_coarse_grid_parameter_distribution`
- 예상: `filter_tf` 5개 값 모두 등장
- 실제: Coarse Grid는 min/mid/max만 사용 → 3개 값만 등장

**수정**:
```python
# Before (잘못됨)
expected_tfs = set(META_PARAM_RANGES['filter_tf'])  # 5개
actual_tfs = set(tf_counts.keys())
assert actual_tfs == expected_tfs  # 실패!

# After (올바름)
assert len(tf_counts) == 3, f"filter_tf 값 개수: {len(tf_counts)} (예상: 3)"
# Coarse Grid는 ['2h', '6h', '1d'] 3개만 사용 (min, mid, max)
```

---

### 3. **타임스탬프 기간 계산 검증 오류** (1개 테스트 실패)

**문제**: `test_overnight_trade_duration`
- 예상: 하룻밤 거래 = 1일
- 실제: `(datetime - datetime).days`는 24시간 단위로 계산

**실제 동작** (from `core/optimizer.py:658`):
```python
duration = (end_time - start_time).days
```

**예시**:
- 22:00 (1/15) ~ 02:00 (1/16) = 4시간 = **0일** (24시간 미만)
- 22:00 (1/15) ~ 22:01 (1/16) = 24시간 1분 = **1일**

**수정**:
```python
# Before (잘못됨)
assert duration == 1, f"Overnight trade should have 1 day duration: {duration}"

# After (올바름)
assert duration == 0, f"Overnight trade (4 hours) should have 0 days duration: {duration}"
# 실제 구현: (datetime - datetime).days는 24시간 단위
```

---

## ✅ 수정 완료 파일

1. `test_coarse_grid_coverage.py`
   - Line 134-137: Coarse Grid 크기 주석 수정
   - Line 241-242: filter_tf 검증 로직 수정 (5개 → 3개)

2. `test_optimal_params_validation.py`
   - Line 66: `trail_start_r` 1.2 → 1.5
   - Line 91: `trail_start_r` 1.2 → 1.5
   - Line 110: `trail_start_r` 1.2 → 1.5
   - Line 133: `trail_dist_r` 범위 밖 값 0.1 → 0.5
   - Line 145: `trail_start_r` 1.2 → 1.5
   - Line 174: `trail_start_r` 1.2 → 1.5
   - Line 198: `trail_dist_r` 최소값 0.005 → 0.01
   - Line 211: `trail_dist_r` 최대값 0.05 → 0.3
   - Line 228: `trail_start_r` 1.2 → 1.5
   - Line 254: `trail_start_r` 1.2 → 1.5
   - Line 262: `trail_start_r` 1.2 → 1.5

3. `test_timestamp_accuracy.py`
   - Line 111-116: overnight 거래 기간 검증 로직 수정 (1일 → 0일)

---

## 📊 예상 결과

**수정 전**:
```
총 테스트: 28
통과: 22
실패: 6
성공률: 78.6%
```

**수정 후 (예상)**:
```
총 테스트: 28
통과: 28
실패: 0
성공률: 100.0%
```

---

## 🚀 재실행 방법

```bash
# 프로젝트 루트에서 실행
python tests/v722_validation/run_all_tests.py
```

**예상 출력**:
```
======================================================================
최종 결과
======================================================================
총 테스트: 28
통과: 28
실패: 0
성공률: 100.0%

======================================================================
✅ 모든 테스트 통과!
======================================================================
```

---

## 📝 교훈

### 1. 테스트 작성 시 실제 구현 확인 필수
- ❌ 추측으로 테스트 작성
- ✅ 실제 코드/설정 파일 확인 후 작성

### 2. SSOT (Single Source of Truth) 준수
- ❌ 테스트 코드에 하드코딩된 값
- ✅ `META_PARAM_RANGES`에서 직접 가져오기

### 3. 표준 라이브러리 동작 이해
- ❌ `(datetime - datetime).days`가 날짜 경계로 계산된다고 추측
- ✅ 실제론 24시간 단위로 계산됨

---

## 🔍 향후 개선 사항

### 테스트 데이터 동적 생성

**현재** (하드코딩):
```python
optimal_params = {
    'atr_mult': 1.5,
    'trail_start_r': 1.5,  # 수동으로 META_PARAM_RANGES에서 선택
    ...
}
```

**개선안** (동적 생성):
```python
import random
from config.meta_ranges import META_PARAM_RANGES

optimal_params = {
    'atr_mult': random.choice(META_PARAM_RANGES['atr_mult']),
    'trail_start_r': random.choice(META_PARAM_RANGES['trail_start_r']),
    ...
}
```

**장점**:
- META_PARAM_RANGES 변경 시 테스트 자동 적응
- 하드코딩 불일치 방지

---

**작성**: Claude Sonnet 4.5
**작성일**: 2026-01-17
**버전**: v7.22
