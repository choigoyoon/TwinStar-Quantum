# v7.22 검증 테스트 스위트

v7.22 그리드 기반 Meta 최적화 + 타임스탬프 기능의 신뢰성을 보증하기 위한 검증 테스트 모음입니다.

## 📁 테스트 파일 구조

```
tests/v722_validation/
├── README.md                                # 이 문서
├── run_all_tests.py                         # 전체 테스트 실행 스크립트
│
├── test_coarse_grid_coverage.py             # Coarse Grid 커버리지 검증 (5개 테스트)
├── test_optimal_params_validation.py        # optimal_params 유효성 검증 (9개 테스트)
└── test_timestamp_accuracy.py               # 타임스탬프 정확성 검증 (14개 테스트)
```

**총 28개 테스트**, **959줄 코드**

---

## 🚀 실행 방법

### 방법 1: 전체 테스트 실행 (권장)

```bash
# 프로젝트 루트에서 실행
python tests/v722_validation/run_all_tests.py
```

**출력 예시**:
```
======================================================================
v7.22 검증 테스트 실행 시작
======================================================================

======================================================================
Test Suite 1: Coarse Grid Coverage (5 tests)
======================================================================

--- Test: Coarse Grid Structure ---
✓ Coarse Grid 크기: 405개
✓ 파라미터 수: 5개
✅ PASSED

--- Test: Coarse Grid Includes Extremes ---
✓ 모든 파라미터의 min/max 값 포함
✅ PASSED

...

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

### 방법 2: 개별 테스트 실행

```bash
# Coarse Grid 커버리지 테스트
python tests/v722_validation/test_coarse_grid_coverage.py

# optimal_params 유효성 테스트
python tests/v722_validation/test_optimal_params_validation.py

# 타임스탬프 정확성 테스트
python tests/v722_validation/test_timestamp_accuracy.py
```

---

### 방법 3: pytest 사용

```bash
# 전체 테스트
pytest tests/v722_validation/ -v -s

# 개별 테스트
pytest tests/v722_validation/test_coarse_grid_coverage.py -v -s
pytest tests/v722_validation/test_optimal_params_validation.py -v -s
pytest tests/v722_validation/test_timestamp_accuracy.py -v -s
```

---

## 📊 테스트 상세

### Test Suite 1: Coarse Grid Coverage (5개 테스트, 277줄)

**목적**: Coarse Grid가 파라미터 공간을 충분히 커버하는지 검증

| # | 테스트 이름 | 검증 내용 | 성공 기준 |
|---|------------|----------|----------|
| 1 | `test_coarse_grid_structure` | Grid 구조 (min/mid/max) | 300-500개 조합 |
| 2 | `test_coarse_grid_includes_extremes` | 극값 포함 여부 | 모든 파라미터 min/max 포함 |
| 3 | `test_coarse_grid_coverage_random_samples` | 랜덤 샘플 커버율 | ≥50% |
| 4 | `test_coarse_grid_coverage_top_results` | 상위 20% 커버율 | ≥40% |
| 5 | `test_coarse_grid_parameter_distribution` | 파라미터 분포 균등성 | 각 값 ≥10회 등장 |

**핵심 알고리즘**:
- `generate_coarse_grid()` - min/mid/max 조합 생성
- `calculate_distance()` - 정규화 거리 계산 (L1 norm)
- `calculate_coverage()` - 커버율 계산 (threshold=0.3)

**예상 조합 수**: 3×3×3×3×5 = **405개**

---

### Test Suite 2: Optimal Params Validation (9개 테스트, 341줄)

**목적**: optimal_params의 유효성과 완전성 검증

| # | 테스트 이름 | 검증 내용 | 성공 기준 |
|---|------------|----------|----------|
| 1 | `test_required_parameters_exist` | 필수 파라미터 존재 | 5개 모두 존재 |
| 2 | `test_parameter_types` | 타입 정확성 | 숫자 4개, 문자열 1개 |
| 3 | `test_parameter_values_in_range` | 범위 검증 | META_PARAM_RANGES 내 |
| 4 | `test_parameter_values_out_of_range` | 범위 밖 감지 | 잘못된 값 감지 |
| 5 | `test_optimal_params_matches_best_result` | best_result 일치 | 100% 일치 |
| 6 | `test_parameter_precision` | 정밀도 검증 | 소수점 3자리 이하 |
| 7 | `test_edge_case_extreme_values` | 극값 처리 | min/max 조합 정상 |
| 8 | `test_optimal_params_serialization` | JSON 직렬화 | 정상 변환 |
| 9 | `test_optimal_params_from_meta_result` | Meta 결과 통합 | 추출 정상 |

**핵심 함수**:
- `validate_param_in_range()` - 파라미터 범위/타입/이산값 검증

**필수 파라미터** (5개):
1. `atr_mult` (float)
2. `filter_tf` (str)
3. `trail_start_r` (float)
4. `trail_dist_r` (float)
5. `entry_validity_hours` (float)

---

### Test Suite 3: Timestamp Accuracy (14개 테스트, 341줄)

**목적**: 타임스탬프 추출 및 백테스트 기간 계산의 정확성 검증

| # | 테스트 이름 | 검증 내용 | 성공 기준 |
|---|------------|----------|----------|
| 1 | `test_single_trade_timestamps` | 단일 거래 추출 | entry/exit 정확 |
| 2 | `test_multiple_trades_timestamps` | 복수 거래 추출 | 첫/마지막 정확 |
| 3 | `test_empty_trades_timestamps` | 거래 0개 처리 | (None, None, 0) |
| 4 | `test_single_day_trade_duration` | 같은 날 거래 | 0일 |
| 5 | `test_overnight_trade_duration` | 하룻밤 거래 | 1일 |
| 6 | `test_multi_day_trade_duration` | 여러 날 거래 | 정확한 일수 |
| 7 | `test_duration_calculation_precision` | 기간 계산 정밀도 | 날짜 단위 (시간 무시) |
| 8 | `test_datetime_format` | datetime 형식 | 처리 정상 |
| 9 | `test_pandas_timestamp_format` | pandas Timestamp | 처리 정상 |
| 10 | `test_string_timestamp_format` | ISO 8601 문자열 | 처리 정상 |
| 11 | `test_leap_year_february` | 윤년 2월 | 2/28→3/1 = 2일 |
| 12 | `test_year_boundary` | 연도 경계 | 12/30→1/2 = 3일 |
| 13 | `test_timezone_aware_timestamps` | 타임존 인식 | 처리 정상 |
| 14 | `test_very_long_duration` | 장기 기간 (1년+) | 정확한 일수 |

**핵심 함수**:
- `extract_timestamps_from_trades()` (core.optimizer)
- `create_mock_trade()` - 더미 거래 데이터 생성

**특수 케이스**:
- 23:59:59 차이 → **0일** (같은 날)
- 00:00:01 차이 (다음 날) → **1일**
- 2024년 윤년: 2/28 → 2/29 → 3/1 = **2일**

---

## ✅ 검증 완료 시 기대 효과

### 정량적 지표

| 항목 | 현재 | 목표 | 개선율 |
|------|------|------|--------|
| 테스트 커버리지 | 30% | 100% | +233% |
| Coarse Grid 정확성 | 미검증 | 검증 완료 | - |
| optimal_params 신뢰도 | 미검증 | 100% | - |
| 타임스탬프 정확도 | 미검증 | 100% | - |

### 정성적 효과

1. **신뢰성 보증**: 핵심 알고리즘의 수학적 정확성 보증
2. **유지보수성 향상**: 회귀 방지, 리팩토링 안전성
3. **사용자 신뢰**: 검증된 시스템으로 프로덕션 준비
4. **개발 속도**: 빠른 버그 발견 및 수정

---

## 📋 다음 단계 (검증 계획서 기준)

### 우선순위 1 (핵심 알고리즘) - 진행 중 (3/4 완료)

완료:
- ✅ test_coarse_grid_coverage.py (15분)
- ✅ test_optimal_params_validation.py (15분)
- ✅ test_timestamp_accuracy.py (15분)

**다음 작업** (30-50분):
1. `test_fine_grid_convergence.py` (30분)
   - Phase 1→2 개선율 ≥5% 검증
   - Phase 2→3 개선율 측정
   - **실제 OHLCV 데이터 필요** (최소 1,000개 캔들)

2. `test_range_refinement.py` (20분)
   - ±50%/±20% 범위가 실제 최적값 포함하는지

3. `test_confidence_intervals.py` (15분)
   - 상위 10% 결과 기반 구간 계산

### 우선순위 2-5 (대기)

- 우선순위 2: optimal_params 신뢰성 (1-2시간)
- 우선순위 3: 타임스탬프 정확성 추가 (1-2시간)
- 우선순위 4: UI 통합 검증 (2-3시간)
- 우선순위 5: E2E 검증 (2-3시간)

**총 예상 시간**: ~10시간 (병렬 실행 시 5-6시간)

---

## 🔧 문제 해결

### ImportError: No module named 'config'

**원인**: 프로젝트 루트가 sys.path에 없음

**해결**:
```python
# 각 테스트 파일 상단에 이미 추가됨
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

### pytest 없이 실행 시 에러

**해결**: 모든 테스트 파일은 pytest 없이도 실행 가능하도록 작성되었습니다.

```bash
# 직접 실행
python tests/v722_validation/test_coarse_grid_coverage.py
```

---

## 📚 참고 문서

1. **검증 계획서**: `docs/V722_VALIDATION_PLAN.txt`
   - 전체 검증 전략 및 우선순위
   - 19개 테스트 세부 사항

2. **작업 로그**: `docs/WORK_LOG_20260117_V722_VALIDATION.txt`
   - 테스트 작성 과정 기록
   - 기술적 고려사항

3. **기존 테스트**:
   - `test_grid_meta.py` (210줄) - 그리드 Meta 구조 검증
   - `test_v722_integration.py` (204줄) - v7.22 통합 검증

---

## 📊 통계

- **테스트 파일**: 3개 + 1개 (실행 스크립트)
- **총 테스트**: 28개
- **총 라인 수**: 959줄
- **작성 시간**: 45분
- **Pyright 에러**: 0개

---

**작성**: Claude Sonnet 4.5
**작성일**: 2026-01-17
**버전**: v7.22
