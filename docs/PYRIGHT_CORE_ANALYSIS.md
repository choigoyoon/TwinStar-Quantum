# Pyright Core Error Analysis
## 일자: 2026-01-14

## 📊 오류 통계 (VS Code Problems)

### 파일별 오류 분포
| 디렉토리 | 파일 수 | 주요 오류 유형 |
|---------|---------|---------------|
| tools/archive_diagnostic/ | 50+ | Syntax errors, reconfigure(), indentation |
| tests/ | 10+ | reportAttributeAccessIssue, Optional access |
| GUI/ | 3 | Optional member access |

### 오류 유형별 분류

#### 1. **CRITICAL** - Syntax Errors (즉시 수정 필요)
| 파일 | 라인 | 오류 |
|------|------|------|
| tools/archive_diagnostic/debug_audit.py | 17-18 | 들여쓰기 불일치, 예기치 않은 들여쓰기 |
| tools/archive_diagnostic/debug_detailed_audit.py | 18-19 | 들여쓰기 불일치 |
| tools/archive_diagnostic/debug_gui_audit.py | 13, 18-19, 40-41 | try 절 누락, 들여쓰기, 변수 미정의 |
| tools/archive_diagnostic/locate_multiline_lines.py | 13, 18, 20, 25-26 | try 절 누락, 들여쓰기, 변수 미정의 |
| tools/archive_diagnostic/verify_cleanup_final.py | 34-35 | 한글 변수명, 문자열 미종료 |
| tools/archive_diagnostic/verify_core_cleanup.py | 29-30 | 한글 변수명, 문자열 미종료 |
| tools/archive_diagnostic/verify_except.py | 2 | 한글 변수명 사용 |
| tools/archive_diagnostic/generate_core_report.py | 14 | 예기치 않은 들여쓰기 |

#### 2. **HIGH** - reportAttributeAccessIssue (타입 안정성)
| 파일 | 라인 | 오류 내용 |
|------|------|----------|
| tests/verify_full_pipeline.py | 61-62, 80, 99 | AutoPipelineWidget 속성 미정의 (_prog, _simulate_progress, _run_verification) |
| tests/verify_gui_robustness.py | 31, 45 | setCheckState, _run_verification 접근 불가 |
| tests/verify_multi_trading_system.py | 144-145 | total_trades 속성 접근 불가 (None) |
| tools/archive_diagnostic/functional_test.py | 276, 279, 286-287, 295, 360 | Widget 속성 접근 불가 (strategy, preset_combo, param_widgets, control_panel, chk_4h) |
| tools/archive_diagnostic/system_bloodflow_check.py | 194-195, 204-205, 221 | Widget 속성 접근 불가 |
| tools/archive_diagnostic/verify_build.py | 39 | SignalDetector import 오류 |
| tools/archive_diagnostic/param_consistency_check.py | 333 | AlphaX7Core.generate_signals 접근 불가 |

#### 3. **HIGH** - reportUndefinedVariable (변수 미정의)
| 파일 | 라인 | 변수명 |
|------|------|--------|
| tools/archive_diagnostic/debug_gui_audit.py | 41 | e |
| tools/archive_diagnostic/locate_multiline_lines.py | 26 | e |
| tools/archive_diagnostic/scan_risky_patterns.py | 4 | rstr, Path |
| tools/archive_diagnostic/system_doctor.py | 152 | sys |
| tools/archive_diagnostic/verify_calculations.py | 5 | rstr, Path |
| tools/archive_diagnostic/verify_cleanup_final.py | 34 | 잔여 |
| tools/archive_diagnostic/verify_complete.py | 6 | rstr, Path |
| tools/archive_diagnostic/verify_core_cleanup.py | 29 | 잔여, 확인 |
| tools/archive_diagnostic/verify_deep.py | 5 | rstr, Path |
| tools/archive_diagnostic/verify_except.py | 2 | 상세 |

#### 4. **MEDIUM** - TextIO.reconfigure() (환경 문제)
약 30개 파일에서 `sys.stdout.reconfigure(encoding='utf-8')` 패턴 사용
- Python 3.7+ 필요
- Windows 콘솔 UTF-8 인코딩 처리

#### 5. **MEDIUM** - reportOptionalMemberAccess (PyQt6 Optional 반환)
| 파일 | 라인 | 오류 |
|------|------|------|
| tests/verify_gui_robustness.py | 31 | setCheckState 접근 (None 가능) |
| tests/verify_multi_trading_system.py | 144-145 | total_trades 접근 (None 가능) |

#### 6. **LOW** - reportOperatorIssue, reportCallIssue (타입 불일치)
- tools/archive_diagnostic/research_seed_bug.py:31 - int vs int|None 비교
- tools/archive_diagnostic/reproduce_upbit_limit.py:13 - Optional 연산
- tools/archive_diagnostic/functional_test.py:256 - 누락된 symbol 매개변수

---

## 🎯 수정 전략

### Phase 1: 레거시 코드 정리 (강력 권장)
**대상**: `tools/archive_diagnostic/` 전체 (50+ 파일)

**사유**:
- Syntax 오류 다수 (10+ 파일)
- 한글 변수명 사용 (문법 오류 유발)
- 일회성 진단 스크립트
- 프로덕션 코드 아님

**조치**:
```bash
# 백업 후 삭제
git mv tools/archive_diagnostic tools/archive_diagnostic.backup
echo "tools/archive_diagnostic.backup/" >> .gitignore
```

**효과**: 200+ 오류 즉시 제거

### Phase 2: 테스트 코드 수정 (필수)
**대상**: `tests/verify_*.py`, `tests/*_test.py`

**주요 수정**:
1. Mock 객체 속성 정의 추가
2. Optional 반환값 체크
3. 누락된 import 추가

### Phase 3: GUI 코드 안정화 (권장)
**대상**: GUI/*.py에서 Optional 미체크 부분

**패턴**:
```python
# Before
item.setCheckState(0)  # item이 None일 수 있음

# After
if item:
    item.setCheckState(Qt.CheckState.Unchecked)
```

---

## 📋 즉시 실행 가능한 조치

### 1. archive_diagnostic 폴더 처리
```bash
# Option A: 완전 삭제 (권장)
rm -rf tools/archive_diagnostic/

# Option B: 백업 후 숨기기
mv tools/archive_diagnostic/ tools/.archive_diagnostic_backup/
```

### 2. 문법 오류 파일 개별 수정 (삭제 안할 경우)
- debug_audit.py: 들여쓰기 수정
- debug_detailed_audit.py: 들여쓰기 수정
- verify_cleanup_final.py: 한글 변수명 제거
- verify_core_cleanup.py: 한글 변수명 제거
- verify_except.py: 한글 변수명 제거

### 3. 테스트 코드 수정
- tests/verify_full_pipeline.py: AutoPipelineWidget 모킹 개선
- tests/verify_gui_robustness.py: Optional 체크 추가
- tests/verify_multi_trading_system.py: Optional 체크 추가

---

## 🚨 권장 사항

**1단계: 레거시 정리 (즉시)**
- tools/archive_diagnostic/ 삭제 → 200+ 오류 제거

**2단계: 핵심 테스트 수정 (필수)**
- tests/ 폴더의 실제 사용 테스트만 유지
- verify_* 스크립트 정리

**3단계: Pyright 재검증**
```bash
python -m pyright --outputjson > pyright_clean.json
```

**예상 결과**: 1,405개 → 약 300-400개로 감소

---

## 📊 최종 목표

| 항목 | 현재 | 목표 |
|-----|------|-----|
| 총 오류 | 1,405개 | <300개 |
| Syntax 오류 | 20+ | 0개 |
| Archive 오류 | 200+ | 0개 (삭제) |
| Test 오류 | 50+ | <10개 |
| 타입 경고 | 900+ | 허용 (런타임 영향 없음) |

---

작성: Claude Sonnet 4.5
일자: 2026-01-14
