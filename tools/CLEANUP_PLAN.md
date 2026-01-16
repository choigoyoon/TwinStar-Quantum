# 진단 스크립트 정리 계획

## 분류 기준

### ✅ 유지 (프로덕션/CI 필수)
- `verify_production_ready.py` - 프로덕션 준비 검증 (최신, 필수)
- `check_dependencies.py` - 의존성 확인 (CI 가능)
- `test_symbol_normalization_manual.py` - 심볼 정규화 검증 (Phase A-3)

### 📦 아카이브 (개발 완료, 히스토리)

#### Phase 검증 스크립트 (개발 완료)
- `verify_phase8_1.py` - Phase 8-1 완료
- `verify_phase8_3.py` - Phase 8-3 완료
- `verify_phase9_integration.py` - Phase 9 완료
- `verify_phase10_2.py` - Phase 10-2 완료
- `analyze_phase10_2.py` - Phase 10-2 분석

#### GUI 검증 스크립트 (v7.18 완료)
- `verify_gui_comprehensive.py` - 포괄적 GUI 검증
- `verify_gui_functions.py` - GUI 함수 검증
- `verify_gui_integration.py` - GUI 통합 검증
- `check_gui_refactoring.py` - GUI 리팩토링 확인
- `check_module_functions.py` - 모듈 함수 확인
- `GUI/verify_all_modules.py` - 전체 모듈 검증

#### 최적화 실험 스크립트 (프리셋 완성)
- `test_atr_mult_quick.py` - ATR 배수 테스트
- `test_filter_tf_hypothesis.py` - filter_tf 가설 검증
- `test_final_combination.py` - 최종 조합 테스트
- `test_optimization_impact.py` - 최적화 영향 분석
- `test_optimization_modes.py` - 최적화 모드 테스트
- `test_optimizer_200k.py` - 대용량 옵티마이저 테스트
- `test_optimizer_simple.py` - 간단한 옵티마이저 테스트
- `test_previous_optimal.py` - 이전 최적값 테스트
- `analyze_indicator_sensitivity.py` - 지표 민감도 분석
- `analyze_optimization_results.py` - 최적화 결과 분석
- `analyze_deep_results.py` - Deep 모드 결과 분석

#### 워크플로우 테스트 (기능 완성)
- `test_preset_workflow.py` - 프리셋 워크플로우
- `test_real_workflow.py` - 실제 워크플로우
- `test_bulk_collection.py` - 대량 수집 테스트
- `test_phase4_ui.py` - Phase 4 UI 테스트
- `test_timezone_fix.py` - 시간대 수정 테스트

#### 시스템 검증 (개발 완료)
- `verify_connections.py` - 연결 검증
- `verify_consistency.py` - 일관성 검증
- `verify_full_system.py` - 전체 시스템 검증
- `verify_optimization_consistency.py` - 최적화 일관성
- `verify_required_methods.py` - 필수 메서드 검증
- `verify_requirements.py` - 요구사항 검증
- `verify_trading_logic.py` - 트레이딩 로직 검증
- `verify_unified_bot_structure.py` - 통합 봇 구조 검증
- `full_backtest_verification.py` - 전체 백테스트 검증

#### 프로젝트 분석 (일회성)
- `analyze_alphax7.py` - Alpha X7 분석
- `analyze_density.py` - 밀도 분석
- `analyze_dryrun_results.py` - Dryrun 결과 분석
- `analyze_flow.py` - 플로우 분석
- `analyze_project.py` - 프로젝트 분석

#### 환경 체크 (일회성)
- `check_bybit_methods.py` - Bybit 메서드 확인
- `check_config_dryrun.py` - Config dryrun 확인
- `check_dryrun_status.py` - Dryrun 상태 확인
- `check_duplicates.py` - 중복 확인
- `check_existing_data.py` - 기존 데이터 확인
- `check_file_sizes.py` - 파일 크기 확인
- `check_layout.py` - 레이아웃 확인
- `check_sizes_simple.py` - 단순 크기 확인
- `check_ux.py` - UX 확인

### ❌ 삭제 (중복/불필요)
없음 (모두 히스토리 가치 있음)

## 실행 계획

### 1단계: 아카이브 디렉토리 생성
```bash
mkdir -p tools/archive_diagnostic_20260117
```

### 2단계: Phase 검증 스크립트 이동 (5개)
```bash
mv tools/verify_phase*.py tools/archive_diagnostic_20260117/
mv tools/analyze_phase*.py tools/archive_diagnostic_20260117/
```

### 3단계: GUI 검증 스크립트 이동 (6개)
```bash
mv tools/verify_gui*.py tools/archive_diagnostic_20260117/
mv tools/check_gui*.py tools/archive_diagnostic_20260117/
mv tools/check_module*.py tools/archive_diagnostic_20260117/
mv GUI/verify_all_modules.py tools/archive_diagnostic_20260117/
```

### 4단계: 최적화 실험 스크립트 이동 (11개)
```bash
mv tools/test_atr*.py tools/archive_diagnostic_20260117/
mv tools/test_filter*.py tools/archive_diagnostic_20260117/
mv tools/test_final*.py tools/archive_diagnostic_20260117/
mv tools/test_optimization*.py tools/archive_diagnostic_20260117/
mv tools/test_optimizer*.py tools/archive_diagnostic_20260117/
mv tools/test_previous*.py tools/archive_diagnostic_20260117/
mv tools/analyze_indicator*.py tools/archive_diagnostic_20260117/
mv tools/analyze_optimization*.py tools/archive_diagnostic_20260117/
mv tools/analyze_deep*.py tools/archive_diagnostic_20260117/
```

### 5단계: 워크플로우 테스트 이동 (5개)
```bash
mv tools/test_preset*.py tools/archive_diagnostic_20260117/
mv tools/test_real*.py tools/archive_diagnostic_20260117/
mv tools/test_bulk*.py tools/archive_diagnostic_20260117/
mv tools/test_phase4*.py tools/archive_diagnostic_20260117/
mv tools/test_timezone*.py tools/archive_diagnostic_20260117/
```

### 6단계: 시스템 검증 스크립트 이동 (9개)
```bash
mv tools/verify_connections.py tools/archive_diagnostic_20260117/
mv tools/verify_consistency.py tools/archive_diagnostic_20260117/
mv tools/verify_full*.py tools/archive_diagnostic_20260117/
mv tools/verify_optimization*.py tools/archive_diagnostic_20260117/
mv tools/verify_required*.py tools/archive_diagnostic_20260117/
mv tools/verify_requirements.py tools/archive_diagnostic_20260117/
mv tools/verify_trading*.py tools/archive_diagnostic_20260117/
mv tools/verify_unified*.py tools/archive_diagnostic_20260117/
mv tools/full_backtest*.py tools/archive_diagnostic_20260117/
```

### 7단계: 프로젝트 분석 스크립트 이동 (5개)
```bash
mv tools/analyze_alphax7.py tools/archive_diagnostic_20260117/
mv tools/analyze_density.py tools/archive_diagnostic_20260117/
mv tools/analyze_dryrun*.py tools/archive_diagnostic_20260117/
mv tools/analyze_flow.py tools/archive_diagnostic_20260117/
mv tools/analyze_project.py tools/archive_diagnostic_20260117/
```

### 8단계: 환경 체크 스크립트 이동 (9개)
```bash
mv tools/check_bybit*.py tools/archive_diagnostic_20260117/
mv tools/check_config*.py tools/archive_diagnostic_20260117/
mv tools/check_dryrun*.py tools/archive_diagnostic_20260117/
mv tools/check_duplicates.py tools/archive_diagnostic_20260117/
mv tools/check_existing*.py tools/archive_diagnostic_20260117/
mv tools/check_file*.py tools/archive_diagnostic_20260117/
mv tools/check_layout.py tools/archive_diagnostic_20260117/
mv tools/check_sizes*.py tools/archive_diagnostic_20260117/
mv tools/check_ux.py tools/archive_diagnostic_20260117/
```

## 통계

- **총 스크립트**: 51개
- **유지**: 3개 (6%)
- **아카이브**: 48개 (94%)
- **삭제**: 0개

## 결과

### tools/ 디렉토리 (유지 3개)
- verify_production_ready.py
- check_dependencies.py
- test_symbol_normalization_manual.py

### tools/archive_diagnostic_20260117/ (48개)
- Phase 검증: 5개
- GUI 검증: 6개
- 최적화 실험: 11개
- 워크플로우: 5개
- 시스템 검증: 9개
- 프로젝트 분석: 5개
- 환경 체크: 9개

### GUI/ 디렉토리
- verify_all_modules.py 제거
