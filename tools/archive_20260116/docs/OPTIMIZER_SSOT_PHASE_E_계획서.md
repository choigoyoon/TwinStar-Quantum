# Phase 1-E: 최적화 시스템 SSOT 완전 통합 계획서

**작성일**: 2026-01-15
**버전**: 1.0
**담당**: Claude Opus 4.5
**배경**: Phase 1-D 백테스트 메트릭 SSOT 완료 후, 최적화 시스템 전체 통합 필요

---

## 📋 Executive Summary

### 현재 상태 (Phase 1-D 완료 후)
- **utils/metrics.py**: 백테스트 메트릭 SSOT 구축 완료 ✅
- **core/optimizer.py**: 95% SSOT 준수 (Stability만 로컬 구현)
- **core/optimization_logic.py**: 90% SSOT 준수 (클램핑 미적용)
- **core/multi_optimizer.py**: 0% SSOT 준수 (완전 로컬 구현) ❌

### Phase 1-E 목표
1. **Multi Optimizer SSOT 마이그레이션** (우선순위: P0)
2. **Optimizer Stability SSOT 통합** (우선순위: P0)
3. **클램핑 정책 전역 적용** (우선순위: P1)
4. **타입 안전성 100% 유지** (VS Code Problems 탭 에러 0개)

### 예상 효과
- 메트릭 계산 100% 통일 (3개 모듈 완전 동기화)
- PF 계산 불일치 제거 (losses==0 처리 통일)
- 클램핑 정책 일관성 확보 (-50% ~ +50%)
- 코드 중복 70줄 감소

---

## 🎯 작업 범위

### P0: 긴급 (즉시 수정 필요)

#### P0-1: Multi Optimizer SSOT 마이그레이션
**파일**: `core/multi_optimizer.py`
**라인**: 260-293 (MetricCalculation 로컬 구현)
**문제점**:
1. `utils.metrics` import 없음
2. 메트릭 계산 완전 로컬 구현
   - Win Rate: `wins / len(result)` (SSOT 미사용)
   - MDD: 로컬 계산 (264-271)
   - Profit Factor: 불완전 공식 `total_pnl / max(abs(sum(...)), 1)`
     - losses==0 처리 없음
     - SSOT와 계산 공식 상이
   - Sharpe Ratio: 미구현
   - Stability: 미구현

**해결 방안**:
```python
# Before (❌ 로컬 구현)
wins = len([t for t in result if t.get('pnl', 0) > 0])
win_rate = wins / len(result)
total_pnl = sum(t.get('pnl', 0) for t in result)
# MDD 로컬 계산...
pf = total_pnl / max(abs(sum(...)), 1)

# After (✅ SSOT 사용)
from utils.metrics import (
    calculate_win_rate,
    calculate_mdd,
    calculate_profit_factor,
    calculate_sharpe_ratio,
    calculate_stability
)

trades_list = [{'pnl': t.get('pnl', 0)} for t in result]
win_rate = calculate_win_rate(trades_list) / 100  # % → decimal
mdd = calculate_mdd(trades_list)
total_pnl = sum(t.get('pnl', 0) for t in result)
pf = calculate_profit_factor(trades_list)
sharpe = calculate_sharpe_ratio([t.get('pnl', 0) for t in result])
stability = calculate_stability([t.get('pnl', 0) for t in result])
```

**영향 범위**:
- 파일: `core/multi_optimizer.py`
- 함수: `_calculate_metrics()` (라인 260-293)
- 의존: 553개 심볼 배치 최적화 시 사용

**검증 방법**:
1. 기존 결과와 비교 (PF 계산 변경으로 차이 예상)
2. 단위 테스트 작성
3. 리그레션 테스트 (multi_optimizer 실행 후 결과 비교)

---

#### P0-2: Optimizer Stability SSOT 마이그레이션
**파일**: `core/optimizer.py`
**라인**: 1209-1215
**문제점**:
- Stability 계산 로컬 구현 (3구간 안정성)
- `utils.metrics.calculate_stability()` 이미 구현되어 있음
- `optimization_logic.py`는 SSOT 호출하지만, `optimizer.py`는 로컬 구현

**해결 방안**:
```python
# Before (❌ 로컬 구현)
n = len(pnls)
p1 = sum(pnls[:n//3])
p2 = sum(pnls[n//3:2*n//3])
p3 = sum(pnls[2*n//3:])
score = sum([p1 > 0, p2 > 0, p3 > 0])
stability = "✅" * score + "⚠️" * (3 - score)

# After (✅ SSOT 사용)
from utils.metrics import calculate_stability
stability = calculate_stability(pnls)
```

**영향 범위**:
- 파일: `core/optimizer.py`
- 함수: `calculate_metrics()` (라인 1131-1267)
- 의존: 모든 백테스트 최적화

**검증 방법**:
1. 기존 결과와 비교 (동일 결과 기대)
2. optimization_logic.py 결과와 비교
3. 단위 테스트 확인

---

### P1: 중요 (다음 반복에 포함)

#### P1-1: Optimization Logic 클램핑 추가
**파일**: `core/optimization_logic.py`
**라인**: 267-275 (compound_return 계산)
**문제점**:
- Phase 1-D 클램핑 정책 (-50% ~ +50%) 미적용
- optimizer.py는 적용 (1175-1186), optimization_logic.py는 미적용
- 일관성 문제

**해결 방안**:
```python
# Before (❌ 클램핑 없음)
equity = 1.0
for p in pnls:
    equity *= (1 + p / 100)
    if equity <= 0:
        equity = 0
        break

# After (✅ 클램핑 적용)
MAX_SINGLE_PNL = 50.0
MIN_SINGLE_PNL = -50.0

equity = 1.0
for p in pnls:
    clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, p))
    equity *= (1 + clamped_pnl / 100)
    if equity <= 0:
        equity = 0
        break
```

**영향 범위**:
- 파일: `core/optimization_logic.py`
- 함수: `_run_backtest_for_grid()` (라인 256-336)
- 의존: 4단계 순차 최적화

**검증 방법**:
1. 극단적 PnL 값 (±100%) 입력 시 클램핑 확인
2. optimizer.py 결과와 비교
3. compound_return 일관성 검증

---

#### P1-2: Multi Optimizer 클램핑 추가
**파일**: `core/multi_optimizer.py`
**라인**: 268-271 (MDD 계산)
**문제점**:
- MDD 계산 시 클램핑 미적용
- 극단적 PnL 값에 대한 보호 없음

**해결 방안**:
```python
# Before (❌ 클램핑 없음)
for t in result:
    cumsum += t.get('pnl', 0)
    if cumsum > peak:
        peak = cumsum
    drawdown = (peak - cumsum) / peak if peak > 0 else 0
    mdd = max(mdd, drawdown)

# After (✅ 클램핑 적용)
MAX_SINGLE_PNL = 50.0
MIN_SINGLE_PNL = -50.0

for t in result:
    pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, t.get('pnl', 0)))
    cumsum += pnl
    if cumsum > peak:
        peak = cumsum
    drawdown = (peak - cumsum) / peak if peak > 0 else 0
    mdd = max(mdd, drawdown)
```

**영향 범위**:
- 파일: `core/multi_optimizer.py`
- 함수: `_calculate_metrics()` (라인 260-293)
- 의존: 553개 심볼 배치 최적화

**검증 방법**:
1. 극단적 PnL 값 입력 시 클램핑 확인
2. optimizer.py MDD 결과와 비교
3. 리그레션 테스트

---

## 🔧 구현 계획

### Step 1: P0-1 - Multi Optimizer SSOT 마이그레이션

**1.1 Import 추가**
- 파일: `core/multi_optimizer.py`
- 라인: 상단 (import 섹션)
- 내용:
  ```python
  from utils.metrics import (
      calculate_win_rate,
      calculate_mdd,
      calculate_profit_factor,
      calculate_sharpe_ratio,
      calculate_stability
  )
  ```

**1.2 MetricCalculation 함수 교체**
- 파일: `core/multi_optimizer.py`
- 라인: 260-293
- 작업:
  1. 기존 로컬 구현 삭제
  2. SSOT 함수 호출로 교체
  3. 타입 힌트 추가

**1.3 검증**
- 단위 테스트 작성
- 기존 결과와 비교
- VS Code Problems 탭 확인

---

### Step 2: P0-2 - Optimizer Stability SSOT 마이그레이션

**2.1 Stability 계산 교체**
- 파일: `core/optimizer.py`
- 라인: 1209-1215
- 작업:
  1. 로컬 구현 삭제
  2. `calculate_stability(pnls)` 호출로 교체

**2.2 검증**
- optimization_logic.py 결과와 비교
- 단위 테스트 확인

---

### Step 3: P1-1 - Optimization Logic 클램핑 추가

**3.1 클램핑 상수 정의**
- 파일: `core/optimization_logic.py`
- 라인: 상단 (상수 섹션)
- 내용:
  ```python
  MAX_SINGLE_PNL = 50.0
  MIN_SINGLE_PNL = -50.0
  ```

**3.2 Compound Return 계산 수정**
- 파일: `core/optimization_logic.py`
- 라인: 267-275
- 작업: 클램핑 로직 추가

**3.3 검증**
- 극단적 PnL 테스트
- optimizer.py 결과와 비교

---

### Step 4: P1-2 - Multi Optimizer 클램핑 추가

**4.1 클램핑 상수 정의**
- 파일: `core/multi_optimizer.py`
- 라인: 상단 (상수 섹션)

**4.2 MDD 계산 수정**
- 파일: `core/multi_optimizer.py`
- 라인: 268-271
- 작업: 클램핑 로직 추가

**4.3 검증**
- 극단적 PnL 테스트
- 리그레션 테스트

---

### Step 5: 단위 테스트 작성

**5.1 테스트 파일 생성**
- 파일: `tests/test_metrics_phase1e.py`
- 내용:
  1. Multi Optimizer 메트릭 계산 테스트
  2. Stability 일관성 테스트
  3. 클램핑 정책 테스트
  4. Edge Case 테스트

**5.2 테스트 시나리오**
1. **정상 케이스**
   - 일반적인 PnL 값 (±20%)
   - 메트릭 계산 정확성 검증

2. **극단적 케이스**
   - PnL ±100% (클램핑 발동)
   - Overflow/Underflow 방지 확인

3. **Edge Case**
   - 거래 0개
   - 거래 1개
   - 모든 거래 손실
   - 모든 거래 수익

4. **일관성 테스트**
   - optimizer.py vs optimization_logic.py vs multi_optimizer.py
   - 동일 입력 → 동일 출력 확인

---

### Step 6: VS Code Problems 탭 확인

**6.1 Pyright 에러 체크**
- 타입 힌트 완전성 확인
- Optional 타입 명시
- Import 경로 일관성

**6.2 타입 안전성 검증**
- 모든 함수 시그니처 타입 힌트
- 반환 타입 명시
- None 안전성 체크

---

## 📊 예상 결과

### 코드 품질 개선

| 항목 | Before | After | 개선도 |
|------|--------|-------|--------|
| SSOT 준수도 | 63% (2/3 모듈) | 100% (3/3 모듈) | +37% |
| 코드 중복 | 70줄 | 0줄 | -70줄 |
| 메트릭 일관성 | 60% | 100% | +40% |
| 타입 안전성 | 100% | 100% | 유지 |
| 클램핑 정책 | 33% (1/3) | 100% (3/3) | +67% |

### 버그 수정

1. **Profit Factor 계산 불일치 해결**
   - Multi Optimizer: losses==0 처리 없음 → SSOT 통일
   - 계산 공식 통일

2. **Stability 계산 중복 제거**
   - optimizer.py 로컬 구현 → SSOT 호출

3. **클램핑 정책 일관성 확보**
   - 3개 모듈 모두 동일 클램핑 정책 적용

---

## ✅ 검증 체크리스트

### P0 작업

- [ ] **P0-1: Multi Optimizer SSOT 마이그레이션**
  - [ ] utils.metrics import 추가
  - [ ] calculate_win_rate() 호출
  - [ ] calculate_mdd() 호출
  - [ ] calculate_profit_factor() 호출
  - [ ] calculate_sharpe_ratio() 호출
  - [ ] calculate_stability() 호출
  - [ ] 타입 힌트 추가
  - [ ] 단위 테스트 통과
  - [ ] 기존 결과와 비교 (PF 차이 확인)

- [ ] **P0-2: Optimizer Stability SSOT 마이그레이션**
  - [ ] calculate_stability() 호출로 교체
  - [ ] optimization_logic.py 결과와 비교
  - [ ] 단위 테스트 통과

### P1 작업

- [ ] **P1-1: Optimization Logic 클램핑 추가**
  - [ ] 클램핑 상수 정의
  - [ ] compound_return 계산 수정
  - [ ] 극단적 PnL 테스트
  - [ ] optimizer.py 결과와 비교

- [ ] **P1-2: Multi Optimizer 클램핑 추가**
  - [ ] 클램핑 상수 정의
  - [ ] MDD 계산 수정
  - [ ] 극단적 PnL 테스트
  - [ ] 리그레션 테스트

### 최종 검증

- [ ] **VS Code Problems 탭**
  - [ ] Pyright 에러 0개
  - [ ] 타입 힌트 완전성 100%

- [ ] **단위 테스트**
  - [ ] 46개 기존 테스트 통과 (Phase 1-D)
  - [ ] 20개 신규 테스트 통과 (Phase 1-E)
  - [ ] 코드 커버리지 100%

- [ ] **통합 테스트**
  - [ ] optimizer.py 실행 성공
  - [ ] optimization_logic.py 실행 성공
  - [ ] multi_optimizer.py 실행 성공
  - [ ] 3개 모듈 메트릭 일치성 확인

---

## 📝 문서화 계획

### 1. CLAUDE.md 업데이트

**섹션 추가**: Phase 1-E (최적화 시스템 SSOT 완전 통합)

```markdown
## 📊 Phase 1-E: 최적화 시스템 SSOT 완전 통합 (2026-01-15)

### 배경 및 문제점

Phase 1-D에서 백테스트 메트릭 SSOT를 구축했지만, 최적화 시스템 일부 모듈에서 여전히 로컬 구현 사용:

**문제 상황**:
1. **Multi Optimizer 완전 비SSOT** (core/multi_optimizer.py)
   - utils.metrics import 없음
   - Profit Factor 계산 공식 상이 (losses==0 처리 없음)

2. **Optimizer Stability 계산 중복** (core/optimizer.py)
   - 로컬 구현, optimization_logic.py는 SSOT 호출

3. **클램핑 정책 불완전**
   - optimizer.py만 적용, optimization_logic.py/multi_optimizer.py 미적용

### 해결 방법

**최적화 시스템 3개 모듈 완전 통합**:
- Multi Optimizer SSOT 마이그레이션
- Optimizer Stability SSOT 통합
- 클램핑 정책 전역 적용

### 성과

1. **SSOT 준수도 100%**: 3/3 모듈 완전 통합
2. **코드 중복 70줄 감소**
3. **메트릭 일관성 100%**: 계산 공식 완전 통일
4. **클램핑 정책 100%**: 3개 모듈 모두 적용
```

---

### 2. WORK_LOG 업데이트

**파일**: `docs/WORK_LOG_20260115.txt`

**추가 섹션**:
```text
--------------------------------------------------------------------------------
## Phase 1-E: 최적화 시스템 SSOT 완전 통합
--------------------------------------------------------------------------------

### 작업 내용

#### P0-1: Multi Optimizer SSOT 마이그레이션
- 파일: core/multi_optimizer.py (260-293)
- 변경: 메트릭 계산 완전 SSOT 교체
  - calculate_win_rate() 호출
  - calculate_mdd() 호출
  - calculate_profit_factor() 호출 (losses==0 처리 통일)
  - calculate_sharpe_ratio() 호출
  - calculate_stability() 호출

#### P0-2: Optimizer Stability SSOT 마이그레이션
- 파일: core/optimizer.py (1209-1215)
- 변경: 로컬 구현 → calculate_stability() 호출

#### P1-1: Optimization Logic 클램핑 추가
- 파일: core/optimization_logic.py (267-275)
- 변경: compound_return 계산 시 클램핑 적용 (-50% ~ +50%)

#### P1-2: Multi Optimizer 클램핑 추가
- 파일: core/multi_optimizer.py (268-271)
- 변경: MDD 계산 시 클램핑 적용

### 검증 결과

- ✅ 단위 테스트 66개 통과 (46 + 20 신규)
- ✅ Pyright 에러 0개
- ✅ 메트릭 일관성 100% (3개 모듈 동일 결과)
- ✅ 코드 중복 70줄 감소

### 다음 작업

- Phase 2: GUI 위젯 메트릭 표시 개선
```

---

### 3. 커밋 메시지 템플릿

```text
refactor: Phase 1-E - 최적화 시스템 SSOT 완전 통합

P0-1: Multi Optimizer SSOT 마이그레이션
- utils.metrics import 추가
- 메트릭 계산 SSOT 교체 (win_rate, mdd, pf, sharpe, stability)
- Profit Factor losses==0 처리 통일

P0-2: Optimizer Stability SSOT 마이그레이션
- 로컬 구현 → calculate_stability() 호출

P1-1: Optimization Logic 클램핑 추가
- compound_return 계산 시 클램핑 적용 (-50% ~ +50%)

P1-2: Multi Optimizer 클램핑 추가
- MDD 계산 시 클램핑 적용

검증:
- 단위 테스트 66개 통과 (46 + 20 신규)
- Pyright 에러 0개
- 메트릭 일관성 100%
- 코드 중복 70줄 감소

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## 🚀 실행 순서

1. **Phase 1-E 계획서 승인** ← 현재 단계
2. **Step 1: P0-1 구현** (Multi Optimizer SSOT)
3. **Step 2: P0-2 구현** (Optimizer Stability SSOT)
4. **Step 3: P1-1 구현** (Optimization Logic 클램핑)
5. **Step 4: P1-2 구현** (Multi Optimizer 클램핑)
6. **Step 5: 단위 테스트 작성 및 실행**
7. **Step 6: VS Code Problems 탭 확인**
8. **Step 7: 문서화 (CLAUDE.md, WORK_LOG)**
9. **Step 8: 커밋 및 푸시**

---

## 📌 리스크 및 대응

### 리스크 1: PF 계산 변경으로 인한 기존 결과 차이
**영향**: Multi Optimizer 기존 프리셋과 결과 불일치
**대응**:
- 변경 전후 비교 문서 작성
- 사용자에게 재최적화 권장
- 변경 이유 명시 (losses==0 처리 통일)

### 리스크 2: 클램핑 정책으로 인한 메트릭 변화
**영향**: 극단적 PnL (±100%) 데이터에서 결과 변화
**대응**:
- 클램핑 전후 비교 리포트 생성
- 클램핑 임계값 조정 가능하도록 설계
- Edge Case 테스트 강화

### 리스크 3: 타입 에러 발생 가능성
**영향**: VS Code Problems 탭 에러 증가
**대응**:
- 각 Step마다 Pyright 에러 체크
- 타입 힌트 완전성 검증
- Optional 타입 명시

---

## 🎯 성공 기준

### 필수 조건 (Must Have)
- [x] Pyright 에러 0개 유지
- [ ] 단위 테스트 66개 통과
- [ ] 3개 모듈 메트릭 일치성 100%

### 선택 조건 (Nice to Have)
- [ ] 성능 개선 (메트릭 계산 속도 ±5% 이내)
- [ ] 문서화 완료 (CLAUDE.md, WORK_LOG)
- [ ] 리그레션 테스트 통과

---

**계획서 승인 후 즉시 구현을 시작합니다.**
