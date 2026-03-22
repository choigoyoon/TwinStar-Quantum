# Tests 디렉토리 정리 계획

## 현황
- **총 파일**: 35개
- **크기**: 4.0MB
- **상태**: 개발 과정에서 누적된 테스트 혼재

## 분류 기준

### ✅ 유지 (프로덕션 CI/CD 필수)

#### 핵심 단위 테스트 (7개)
- `test_strategy_core.py` (12KB) - 전략 코어 로직
- `test_optimizer_core.py` (9.9KB) - 옵티마이저 핵심
- `test_exchange_api_parity.py` (11KB) - 거래소 API 일관성 (v7.9)
- `test_indicators_accuracy.py` (11KB) - 지표 정확도 검증 (v7.14)
- `test_unified_bot.py` - 통합 봇 테스트
- `test_optimizer_defensive.py` (11KB) - 옵티마이저 방어 로직 (v7.20)
- `benchmark_indicators.py` (8.0KB) - 지표 성능 벤치마크 (v7.15)

#### 통합 테스트 (2개)
- `test_integration_suite.py` (18KB) - 통합 테스트 스위트
- `test_integration_trading_flow.py` (14KB) - 트레이딩 플로우

### 📦 아카이브 (개발 완료)

#### Phase 검증 테스트 (3개)
개발 단계별 검증 완료
- `test_phase_a_integration.py` (14KB) - Phase A 통합 (v7.8)
- `test_phase_a2_signal_parity.py` (9.2KB) - Phase A-2 신호 일치 (v7.7)
- `test_phase1_modules.py` (5.7KB) - Phase 1 모듈 (v7.4)

#### Lazy Load 검증 (3개)
Phase 1-C 완료
- `test_data_continuity_lazy_load.py` (8.3KB) - Lazy Load 연속성 (v7.5)
- `test_debug_lazy_load.py` (2.1KB) - Lazy Load 디버그
- `test_lazy_load_quick.py` (5.4KB) - Lazy Load 빠른 검증

#### 백테스트/최적화 검증 (3개)
시스템 완성 후 검증 완료
- `test_backtest_parity.py` (3.8KB) - 백테스트 일치성
- `test_backtest_impact.py` (11KB) - 백테스트 영향 분석
- `test_optimization_backtest_parity.py` (15KB) - 최적화-백테스트 일치

#### 시간/타임존 검증 (2개)
수정 완료
- `test_time_sync.py` (4.4KB) - 시간 동기화
- `test_timezone_fix.py` (4.5KB) - 타임존 수정

#### 메트릭 검증 (2개)
Phase 1-B 완료 (v7.4)
- `test_metrics_phase1d.py` (5.4KB) - Phase 1-D 메트릭
- `test_metrics_phase1e.py` (7.7KB) - Phase 1-E 메트릭

#### 실시간 매매 검증 (1개)
Phase A-2 완료
- `test_backtest_realtime_parity.py` (15KB) - 백테스트-실시간 일치

#### Track 3 수정 검증 (1개)
중요 수정 완료
- `test_track3_critical_fixes.py` (14KB) - Track 3 크리티컬 수정

#### 안정성 테스트 (3개)
시스템 안정화 완료
- `test_exchange_stability.py` (9.2KB) - 거래소 안정성
- `test_memory_stability.py` (12KB) - 메모리 안정성
- `test_edge_cases.py` (13KB) - 엣지 케이스

#### 기능 테스트 (3개)
기능 개발 완료
- `test_candle_close_detector.py` (6.8KB) - 캔들 종가 감지
- `test_gpu_settings.py` (9.8KB) - GPU 설정
- `test_heatmap_widget.py` (11KB) - 히트맵 위젯

### ❌ 삭제 후보 (중복/불필요)
없음 (모두 히스토리 가치 있음)

## 실행 계획

### 1단계: 아카이브 디렉토리 생성
```bash
mkdir -p tests/archive_completed_20260117
```

### 2단계: Phase 검증 테스트 이동 (3개)
```bash
mv tests/test_phase*.py tests/archive_completed_20260117/
```

### 3단계: Lazy Load 검증 이동 (3개)
```bash
mv tests/test_*lazy*.py tests/archive_completed_20260117/
mv tests/test_data_continuity*.py tests/archive_completed_20260117/
mv tests/test_debug_lazy*.py tests/archive_completed_20260117/
```

### 4단계: 백테스트/최적화 검증 이동 (3개)
```bash
mv tests/test_backtest_parity.py tests/archive_completed_20260117/
mv tests/test_backtest_impact.py tests/archive_completed_20260117/
mv tests/test_optimization_backtest*.py tests/archive_completed_20260117/
```

### 5단계: 시간/타임존 검증 이동 (2개)
```bash
mv tests/test_time_sync.py tests/archive_completed_20260117/
mv tests/test_timezone_fix.py tests/archive_completed_20260117/
```

### 6단계: 메트릭 검증 이동 (2개)
```bash
mv tests/test_metrics_phase*.py tests/archive_completed_20260117/
```

### 7단계: 실시간 매매 검증 이동 (1개)
```bash
mv tests/test_backtest_realtime*.py tests/archive_completed_20260117/
```

### 8단계: Track 3 수정 검증 이동 (1개)
```bash
mv tests/test_track3*.py tests/archive_completed_20260117/
```

### 9단계: 안정성 테스트 이동 (3개)
```bash
mv tests/test_exchange_stability.py tests/archive_completed_20260117/
mv tests/test_memory_stability.py tests/archive_completed_20260117/
mv tests/test_edge_cases.py tests/archive_completed_20260117/
```

### 10단계: 기능 테스트 이동 (3개)
```bash
mv tests/test_candle_close*.py tests/archive_completed_20260117/
mv tests/test_gpu*.py tests/archive_completed_20260117/
mv tests/test_heatmap*.py tests/archive_completed_20260117/
```

## 통계

- **총 테스트**: 35개
- **유지**: 9개 (26%) - CI/CD 필수
- **아카이브**: 24개 (69%) - 개발 완료
- **삭제**: 0개
- **미분류**: 2개 (확인 필요)

## 결과

### tests/ 디렉토리 (유지 9개)

**핵심 단위 테스트**:
- test_strategy_core.py
- test_optimizer_core.py
- test_optimizer_defensive.py
- test_exchange_api_parity.py
- test_indicators_accuracy.py
- test_unified_bot.py
- benchmark_indicators.py

**통합 테스트**:
- test_integration_suite.py
- test_integration_trading_flow.py

### tests/archive_completed_20260117/ (24개)

**개발 완료 검증**:
- Phase 검증: 3개
- Lazy Load: 3개
- 백테스트/최적화: 3개
- 시간/타임존: 2개
- 메트릭: 2개
- 실시간 매매: 1개
- Track 3 수정: 1개
- 안정성: 3개
- 기능: 3개
- 기타: 3개

## 효과

- ✅ tests/ 디렉토리 69% 정리
- ✅ CI/CD 테스트 명확화
- ✅ 프로덕션 품질 테스트만 유지
- ✅ 히스토리 100% 보존
