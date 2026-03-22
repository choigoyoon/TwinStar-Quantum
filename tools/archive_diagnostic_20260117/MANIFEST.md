# Archive Manifest - Diagnostic Scripts (2026-01-17)

## 아카이브 정보

- **날짜**: 2026-01-17
- **버전**: v7.18 이후
- **사유**: 프로덕션 준비 - 개발 완료된 진단 스크립트 정리
- **총 파일**: 50개 스크립트

## 아카이브 배경

v7.18 최적화 시스템 완료 후, 개발 과정에서 사용한 진단/검증 스크립트를 정리했습니다.
모든 스크립트는 히스토리 가치가 있어 삭제하지 않고 아카이브로 이동했습니다.

## 디렉토리 구조

```
tools/archive_diagnostic_20260117/
├── Phase 검증 스크립트 (5개)
├── GUI 검증 스크립트 (7개)
├── 최적화 실험 스크립트 (11개)
├── 워크플로우 테스트 (5개)
├── 시스템 검증 스크립트 (9개)
├── 프로젝트 분석 스크립트 (5개)
└── 환경 체크 스크립트 (8개)
```

## 카테고리별 파일 목록

### Phase 검증 스크립트 (5개)
개발 단계별 검증 스크립트 (Phase 8-10 완료)

- `verify_phase8_1.py` - Phase 8-1 검증
- `verify_phase8_3.py` - Phase 8-3 검증
- `verify_phase9_integration.py` - Phase 9 통합 검증
- `verify_phase10_2.py` - Phase 10-2 검증
- `analyze_phase10_2.py` - Phase 10-2 분석

### GUI 검증 스크립트 (7개)
GUI 리팩토링 및 통합 검증 (v7.18 완료)

- `verify_gui_comprehensive.py` - 포괄적 GUI 검증
- `verify_gui_functions.py` - GUI 함수 검증
- `verify_gui_integration.py` - GUI 통합 검증
- `check_gui_refactoring.py` - GUI 리팩토링 확인
- `check_module_functions.py` - 모듈 함수 확인
- `verify_all_modules.py` - 전체 모듈 검증 (GUI/ 디렉토리에서 이동)

### 최적화 실험 스크립트 (11개)
파라미터 최적화 실험 및 분석 (프리셋 완성)

**파라미터 테스트**:
- `test_atr_mult_quick.py` - ATR 배수 빠른 테스트
- `test_filter_tf_hypothesis.py` - filter_tf 가설 검증
- `test_final_combination.py` - 최종 조합 테스트
- `test_previous_optimal.py` - 이전 최적값 테스트

**옵티마이저 테스트**:
- `test_optimization_impact.py` - 최적화 영향 분석
- `test_optimization_modes.py` - 최적화 모드 테스트
- `test_optimizer_200k.py` - 대용량 옵티마이저 (200k 조합)
- `test_optimizer_simple.py` - 간단한 옵티마이저

**결과 분석**:
- `analyze_indicator_sensitivity.py` - 지표 민감도 분석 (21KB)
- `analyze_optimization_results.py` - 최적화 결과 분석 (22KB)
- `analyze_deep_results.py` - Deep 모드 결과 분석

### 워크플로우 테스트 (5개)
실제 사용자 워크플로우 시뮬레이션

- `test_preset_workflow.py` - 프리셋 워크플로우 (14KB)
- `test_real_workflow.py` - 실제 워크플로우 (12KB)
- `test_bulk_collection.py` - 대량 수집 테스트
- `test_phase4_ui.py` - Phase 4 UI 테스트
- `test_timezone_fix.py` - 시간대 수정 테스트

### 시스템 검증 스크립트 (9개)
전체 시스템 무결성 검증

**연결 및 일관성**:
- `verify_connections.py` - 연결 검증
- `verify_consistency.py` - 일관성 검증
- `verify_full_system.py` - 전체 시스템 검증

**최적화 시스템**:
- `verify_optimization_consistency.py` - 최적화 일관성
- `full_backtest_verification.py` - 전체 백테스트 검증 (16KB)

**거래 로직**:
- `verify_trading_logic.py` - 트레이딩 로직 검증
- `verify_unified_bot_structure.py` - 통합 봇 구조 검증

**API 검증**:
- `verify_required_methods.py` - 필수 메서드 검증
- `verify_requirements.py` - 요구사항 검증

### 프로젝트 분석 스크립트 (5개)
프로젝트 구조 및 성능 분석

- `analyze_alphax7.py` - Alpha X7 분석
- `analyze_density.py` - 코드 밀도 분석
- `analyze_dryrun_results.py` - Dryrun 결과 분석
- `analyze_flow.py` - 플로우 분석
- `analyze_project.py` - 프로젝트 분석

### 환경 체크 스크립트 (8개)
개발 환경 점검 도구

**Bybit 관련**:
- `check_bybit_methods.py` - Bybit 메서드 확인

**Config 관련**:
- `check_config_dryrun.py` - Config dryrun 확인
- `check_dryrun_status.py` - Dryrun 상태 확인

**코드 품질**:
- `check_duplicates.py` - 중복 코드 확인
- `check_existing_data.py` - 기존 데이터 확인
- `check_file_sizes.py` - 파일 크기 확인
- `check_layout.py` - 레이아웃 확인
- `check_ux.py` - UX 확인

## 유지된 스크립트 (tools/ 디렉토리)

프로덕션 환경에 필요한 3개 스크립트만 유지:

1. **verify_production_ready.py** (8.6KB)
   - 프로덕션 준비 검증 (6개 카테고리)
   - Entry Points, Import Integrity, Config Files, Storage Init, SSOT Compliance, GUI Launch

2. **check_dependencies.py** (4.6KB)
   - 의존성 확인 (CI/CD 가능)

3. **test_symbol_normalization_manual.py** (2.6KB)
   - 심볼 정규화 검증 (Phase A-3)

## 통계

- **총 스크립트**: 51개 (원본)
- **아카이브**: 50개 (98%)
- **유지**: 3개 (6%)
- **삭제**: 0개 (모두 히스토리 가치 있음)

## 복원 방법

### 개별 파일 복원
```bash
# 특정 스크립트 복원
cp tools/archive_diagnostic_20260117/{filename} tools/

# 예시: GUI 검증 스크립트 복원
cp tools/archive_diagnostic_20260117/verify_gui_comprehensive.py tools/
```

### 카테고리별 복원
```bash
# Phase 검증 스크립트 복원
cp tools/archive_diagnostic_20260117/verify_phase*.py tools/
cp tools/archive_diagnostic_20260117/analyze_phase*.py tools/

# 최적화 실험 스크립트 복원
cp tools/archive_diagnostic_20260117/test_atr*.py tools/
cp tools/archive_diagnostic_20260117/analyze_optimization*.py tools/
```

### 전체 롤백
```bash
# Git 커밋 이전으로 되돌리기
git revert <commit_hash>
```

## 참고 사항

### 개발 완료 마일스톤
- ✅ Phase 8-10: GUI 리팩토링 완료
- ✅ v7.14-v7.18: 지표 SSOT, 메트릭 통합, 최적화 완성
- ✅ 백테스트 위젯: Phase 2 완료 (토큰 기반)
- ✅ 최적화 시스템: Quick/Standard/Deep 모드 (v7.17)
- ✅ 파라미터 범위: filter_tf, entry_validity_hours 정의 (v7.18)

### 검증 완료 항목
- Import 무결성: 18개 핵심 모듈
- SSOT 준수: utils.indicators, utils.metrics
- 타입 안전성: Pyright 에러 0개
- API 일관성: OrderResult 기반 통일

## 아카이브 메타데이터

- **생성일**: 2026-01-17
- **크기**: 약 270KB (50개 파일)
- **Git 상태**: v7.18 완료 후
- **브랜치**: feat/indicator-ssot-integration
- **작성자**: Claude Opus 4.5

---

이 아카이브는 프로젝트 히스토리의 일부이며, 필요 시 언제든 복원 가능합니다.
