# 변경 이력 (CHANGELOG)

## [v1.7.1] - 2026-01-06

### 추가
- 자산 관리 시스템 통합 (`core/capital_manager.py`, `core/trade_common.py`)
- PnL 정밀 추적기 (`core/pnl_tracker.py`)

### 개선
- **Deep Clean**: 프로젝트 전수 구문/인코딩 감사 및 해결 (0 에러)
- **자동 업데이트**: 서버 연동 로직 강화 및 Silent Install 설치 시 구버전 자동 삭제 기능 추가
- **GUI 안정성**: 외부 라이브러리(PyQt5, websockets) Deprecation 경고 전역 차단

### 수정
- `OrderExecutor.calculate_pnl` 인자 불일치 해결 및 수수료 계산 정밀화
- 테스트 코드 내 한글 깨짐 및 SyntaxError 전수 수정

## [v1.7.0] - 2026-01-05

### 추가
- 배치 최적화 기능 (`core/batch_optimizer.py`)
- 자동 파이프라인 위젯 (`GUI/auto_pipeline_widget.py`)
- 통합 로거 유틸리티 (`utils/logger.py`)
- API 재시도 유틸리티 (`utils/retry.py`)
- 상태 관리 유틸리티 (`utils/state_manager.py`)
- 입력 검증 유틸리티 (`utils/validators.py`)
- 캐시 관리 유틸리티 (`utils/cache_manager.py`)

### 개선
- 15m 단일 소스 리샘플링 통일
- 상수 중앙 관리 (`constants.py`, `parameters.py`)
- print() → logging 변환 (63개)
- .gitignore 보안 항목 추가

### 수정
- `auto_scanner.py`: 4H 직접 조회 → 15m + resample
- `unified_backtest.py`: 1h 파일 로드 → 15m + resample
- `data_manager.py`: 1h 저장 함수 deprecated

### 테스트
- 단위 테스트 62개 통과
- 통합 테스트 12개 통과
- 전체 플로우 테스트 28개 통과
- API 심층 테스트 17개 통과
- GUI 통합 테스트 15개 통과

---

## [v1.6.3] - 2025-12-30

### 추가
- 멀티 심볼 백테스트 (`core/multi_symbol_backtest.py`)
- 멀티 옵티마이저 (`core/multi_optimizer.py`)
- 프리셋 헬스 모니터 (`core/preset_health.py`)

### 개선
- EXE 빌드 안정성 향상
- 거래소 어댑터 통일

---

## [v1.6.0] - 2025-12-20

### 추가
- 통합 봇 (`core/unified_bot.py`)
- 포지션 매니저 (`core/position_manager.py`)
- 주문 실행기 (`core/order_executor.py`)

### 개선
- 실시간 트레일링 SL
- dry_run 모드 지원

---

## [v1.5.0] - 2025-12-15

### 추가
- 다중 거래소 지원 (Binance, OKX, Bitget 추가)
- 업비트/빗썸 현물 지원

---

## [v1.0.0] - 2025-12-01

### 최초 릴리스
- AlphaX7 전략 코어
- Bybit 선물 거래 지원
- 기본 백테스트/최적화 기능
- PyQt5 GUI
