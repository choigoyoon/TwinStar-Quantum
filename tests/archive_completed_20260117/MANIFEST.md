# Archive Manifest - Completed Tests (2026-01-17)

## 아카이브 정보

- **날짜**: 2026-01-17
- **버전**: v7.18 이후
- **사유**: 개발 완료된 검증 테스트 정리
- **총 파일**: 21개 테스트

## 아카이브 배경

v7.18 최적화 시스템 완료 후, 각 Phase 및 기능 개발 중 작성된 검증 테스트를 정리했습니다.
모든 테스트는 개발 완료 후 역할을 완수했으며, CI/CD에서는 핵심 테스트만 실행하도록 개선했습니다.

## 유지된 테스트 (tests/ 디렉토리)

프로덕션 CI/CD에 필요한 9개 테스트만 유지:

### 핵심 단위 테스트 (7개)
1. **test_strategy_core.py** (12KB)
   - 전략 코어 로직 테스트
   - 신호 생성, 포지션 관리, PnL 계산

2. **test_optimizer_core.py** (9.9KB)
   - 옵티마이저 핵심 로직
   - 파라미터 그리드 생성, 백테스트 실행

3. **test_optimizer_defensive.py** (11KB)
   - 옵티마이저 방어 로직 (v7.20)
   - 입력 검증, 엣지 케이스 처리

4. **test_exchange_api_parity.py** (11KB)
   - 거래소 API 일관성 검증 (v7.9)
   - OrderResult 기반 통일 확인

5. **test_indicators_accuracy.py** (11KB)
   - 지표 정확도 검증 (v7.14)
   - RSI, ATR, MACD, ADX 정확성

6. **test_unified_bot.py**
   - 통합 봇 테스트
   - 실시간 거래 플로우

7. **benchmark_indicators.py** (8.0KB)
   - 지표 성능 벤치마크 (v7.15)
   - NumPy 벡터화 성능 검증

### 통합 테스트 (2개)
1. **test_integration_suite.py** (18KB)
   - 전체 시스템 통합 테스트
   - 데이터 로드 → 지표 계산 → 신호 생성 → 백테스트

2. **test_integration_trading_flow.py** (14KB)
   - 트레이딩 플로우 통합
   - 실시간 매매 시뮬레이션

## 아카이브된 테스트 (21개)

### Phase 검증 테스트 (3개)
개발 단계별 검증 완료

- **test_phase_a_integration.py** (14KB)
  - Phase A 통합 검증 (v7.8)
  - Symbol 정규화, WebSocket 핸들러

- **test_phase_a2_signal_parity.py** (9.2KB)
  - Phase A-2 신호 일치 검증 (v7.7)
  - 백테스트 vs 실시간 신호 일치율 100%

- **test_phase1_modules.py** (5.7KB)
  - Phase 1 모듈 검증 (v7.4)
  - 메트릭 모듈 SSOT 통합

### Lazy Load 검증 (3개)
Phase 1-C 완료 (v7.5)

- **test_data_continuity_lazy_load.py** (8.3KB)
  - Lazy Load 데이터 연속성
  - 메모리 vs Parquet 분리

- **test_debug_lazy_load.py** (2.1KB)
  - Lazy Load 디버그
  - 워밍업 윈도우 확인

- **test_lazy_load_quick.py** (5.4KB)
  - Lazy Load 빠른 검증
  - 신호 정확도 테스트

### 백테스트/최적화 검증 (3개)
시스템 완성 후 검증 완료

- **test_backtest_parity.py** (3.8KB)
  - 백테스트 일치성
  - 다중 실행 결과 동일성

- **test_backtest_impact.py** (11KB)
  - 백테스트 영향 분석
  - 파라미터 변화에 따른 결과

- **test_optimization_backtest_parity.py** (15KB)
  - 최적화-백테스트 일치
  - 최적화 결과 재현성

### 시간/타임존 검증 (2개)
타임존 수정 완료

- **test_time_sync.py** (4.4KB)
  - 시간 동기화
  - 거래소별 시간 차이 처리

- **test_timezone_fix.py** (4.5KB)
  - 타임존 수정 검증
  - UTC 기준 통일

### 메트릭 검증 (2개)
Phase 1-B 완료 (v7.4)

- **test_metrics_phase1d.py** (5.4KB)
  - Phase 1-D 메트릭
  - MDD, Profit Factor 정확도

- **test_metrics_phase1e.py** (7.7KB)
  - Phase 1-E 메트릭
  - Sharpe, Sortino, Calmar Ratio

### 실시간 매매 검증 (1개)
Phase A-2 완료

- **test_backtest_realtime_parity.py** (15KB)
  - 백테스트-실시간 일치
  - 신호 일치율 95% → 100%

### Track 3 수정 검증 (1개)
중요 수정 완료

- **test_track3_critical_fixes.py** (14KB)
  - Track 3 크리티컬 수정
  - OrderResult, 타입 안전성

### 안정성 테스트 (3개)
시스템 안정화 완료

- **test_exchange_stability.py** (9.2KB)
  - 거래소 안정성
  - 연결 재시도, 에러 핸들링

- **test_memory_stability.py** (12KB)
  - 메모리 안정성
  - 메모리 누수 없음 확인

- **test_edge_cases.py** (13KB)
  - 엣지 케이스
  - 빈 데이터, 극단값 처리

### 기능 테스트 (3개)
기능 개발 완료

- **test_candle_close_detector.py** (6.8KB)
  - 캔들 종가 감지
  - 15분봉 종가 타이밍

- **test_gpu_settings.py** (9.8KB)
  - GPU 설정
  - GPU 가속 옵션

- **test_heatmap_widget.py** (11KB)
  - 히트맵 위젯
  - 최적화 결과 시각화

## 통계

- **총 테스트**: 30개 (원본, __init__.py 제외)
- **유지**: 9개 (30%) - CI/CD 필수
- **아카이브**: 21개 (70%) - 개발 완료
- **삭제**: 0개

## 복원 방법

### 개별 파일 복원
```bash
# 특정 테스트 복원
cp tests/archive_completed_20260117/{filename} tests/

# 예시: Phase A 통합 테스트 복원
cp tests/archive_completed_20260117/test_phase_a_integration.py tests/
```

### 카테고리별 복원
```bash
# Phase 검증 테스트 복원
cp tests/archive_completed_20260117/test_phase*.py tests/

# Lazy Load 테스트 복원
cp tests/archive_completed_20260117/test_*lazy*.py tests/
cp tests/archive_completed_20260117/test_data_continuity*.py tests/
```

### 전체 롤백
```bash
# Git 커밋 이전으로 되돌리기
git revert <commit_hash>
```

## 참고 사항

### 개발 완료 마일스톤
- ✅ Phase A (v7.7-v7.8): 실시간 매매 통합
- ✅ Phase 1 (v7.4-v7.5): 메트릭 SSOT, Lazy Load
- ✅ v7.14-v7.15: 지표 SSOT, NumPy 벡터화
- ✅ v7.18: 최적화 시스템 완성
- ✅ v7.20: 메타 최적화 시스템

### 검증 완료 항목
- 신호 일치율: 70% → 100% (Phase A-2)
- 지표 정확도: 100% (v7.14)
- 지표 성능: 20-86배 빠름 (v7.15)
- API 일관성: 100% (v7.9)
- 타입 안전성: Pyright 에러 0개

### CI/CD 권장 테스트
프로덕션 CI/CD에서는 유지된 9개 테스트만 실행:

```bash
# 핵심 단위 테스트
pytest tests/test_strategy_core.py
pytest tests/test_optimizer_core.py
pytest tests/test_optimizer_defensive.py
pytest tests/test_exchange_api_parity.py
pytest tests/test_indicators_accuracy.py
pytest tests/test_unified_bot.py

# 성능 벤치마크
python tests/benchmark_indicators.py

# 통합 테스트
pytest tests/test_integration_suite.py
pytest tests/test_integration_trading_flow.py
```

## 아카이브 메타데이터

- **생성일**: 2026-01-17
- **크기**: 약 230KB (21개 파일)
- **Git 상태**: v7.18 완료 후
- **브랜치**: feat/indicator-ssot-integration
- **작성자**: Claude Opus 4.5

---

이 아카이브는 프로젝트 개발 히스토리의 일부이며, 필요 시 언제든 복원 가능합니다.
