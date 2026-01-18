# 🏗️ TwinStar Quantum - 프로젝트 구조 및 모듈 가이드

> **버전**: v1.8.4  
> **업데이트**: 2026-01-14  
> **목적**: 프로젝트 구조 파악 및 모듈 연동 가이드

---

## ⚠️ 최근 변경사항 (v1.8.4)

| 변경 | 내용 |
|------|------|
| **PyQt5 → PyQt6** | 전체 GUI 모듈 PyQt6로 마이그레이션 |
| **data_manager 분리** | `GUI/data_manager.py` → `GUI/data_cache.py` (core와 충돌 해결) |
| **import 경로 통일** | `from indicator_generator` → `from utils.indicators` |

---

## 📁 디렉토리 구조

```
TwinStar-Quantum/
├── 📂 core/                 # 핵심 비즈니스 로직 (30개 모듈)
├── 📂 GUI/                  # PyQt6 데스크톱 UI (71개 모듈)
├── 📂 utils/                # 유틸리티 함수 (23개 모듈)
├── 📂 exchanges/            # 거래소 어댑터 (13개 모듈)
├── 📂 strategies/           # 매매 전략 (6개 모듈)
├── 📂 web/                  # 웹 UI (Vue.js + FastAPI)
├── 📂 config/               # 설정 파일
│   ├── 📂 presets/          # 최적화된 프리셋 (JSON)
│   └── 📂 constants/        # 상수 정의
├── 📂 data/                 # 데이터 캐시
├── 📂 docs/                 # 문서
├── 📂 tests/                # 테스트
├── 📂 locales/              # 다국어 지원
└── 📄 *.py                  # 루트 스크립트
```

---

## 🔷 Core 모듈 (핵심 로직)

### 📊 전략 및 백테스트
| 파일 | 용도 | 주요 클래스/함수 |
|------|------|-----------------|
| `strategy_core.py` | 메인 전략 엔진 (AlphaX7) | `AlphaX7Core`, `calculate_mdd()` |
| `unified_backtest.py` | 통합 백테스트 실행 | `run_backtest()` |
| `multi_symbol_backtest.py` | 다중 심볼 백테스트 | `MultiSymbolBacktest` |
| `multi_backtest.py` | 배치 백테스트 | `run_multi_backtest()` |

### 🎯 최적화
| 파일 | 용도 | 주요 클래스/함수 |
|------|------|-----------------|
| `optimizer.py` | 그리드 서치 최적화 | `BacktestOptimizer`, `generate_*_grid()` |
| `optimization_logic.py` | 최적화 엔진 | `OptimizationEngine` |
| `auto_optimizer.py` | 자동 최적화 | `get_or_create_preset()` |
| `batch_optimizer.py` | 배치 최적화 | `BatchOptimizer` |
| `multi_optimizer.py` | 다중 최적화 | `MultiOptimizer` |

### 💰 자본 및 주문 관리
| 파일 | 용도 | 주요 클래스/함수 |
|------|------|-----------------|
| `capital_manager.py` | 자본 관리 (복리/고정) | `CapitalManager` |
| `order_executor.py` | 주문 실행 | `OrderExecutor` |
| `position_manager.py` | 포지션 관리 | `PositionManager` |
| `pnl_tracker.py` | 손익 추적 | `PnLTracker` |

### 🤖 자동 매매
| 파일 | 용도 | 주요 클래스/함수 |
|------|------|-----------------|
| `unified_bot.py` | 통합 봇 엔진 | `UnifiedBot` |
| `multi_trader.py` | 다중 코인 매매 | `MultiTrader` |
| `multi_sniper.py` | 스나이퍼 (고빈도) | `MultiCoinSniper` |
| `dual_track_trader.py` | 듀얼 트랙 (BTC+알트) | `DualTrackTrader` |
| `bot_state.py` | 봇 상태 관리 | `BotState` |

### 🔐 라이선스 및 보안
| 파일 | 용도 | 주요 클래스/함수 |
|------|------|-----------------|
| `license_guard.py` | 라이선스 검증 | `LicenseGuard` |
| `crypto_payment.py` | 암호화폐 결제 | `CryptoPayment` |

### 📡 데이터 관리
| 파일 | 용도 | 주요 클래스/함수 |
|------|------|-----------------|
| `data_manager.py` | 캔들 데이터 관리 | `DataManager` |
| `async_scanner.py` | 비동기 스캐너 | `AsyncScanner` |
| `auto_scanner.py` | 자동 스캐너 | `AutoScanner` |

---

## 🖥️ GUI 모듈 (데스크톱 UI)

### 🏠 메인 윈도우
| 파일 | 용도 | 주요 클래스 |
|------|------|------------|
| `staru_main.py` | 메인 윈도우 | `StarUWindow` |
| `trading_dashboard.py` | 매매 대시보드 | `TradingDashboard` |
| `experimental_main_window.py` | 실험적 UI | `ExperimentalMainWindow` |

### 📊 백테스트/최적화
| 파일 | 용도 | 주요 클래스 |
|------|------|------------|
| `backtest_widget.py` | 백테스트 UI | `BacktestWidget` |
| `backtest_result_widget.py` | 결과 표시 | `BacktestResultWidget` |
| `optimization_widget.py` | 최적화 UI | `OptimizationWidget`, `SingleOptimizerWidget` |
| `result_widget.py` | 결과 위젯 | `ResultWidget` |

### 📈 차트 및 데이터
| 파일 | 용도 | 주요 클래스 |
|------|------|------------|
| `enhanced_chart_widget.py` | 고급 차트 | `EnhancedChartWidget` |
| `data_collector_widget.py` | 데이터 수집 | `DataCollectorWidget` |
| `data_download_widget.py` | 다운로드 UI | `DataDownloadWidget` |
| `data_loader.py` | 데이터 로더 | `DataLoader` |

### ⚙️ 설정 및 도움말
| 파일 | 용도 | 주요 클래스 |
|------|------|------------|
| `settings_widget.py` | 설정 UI | `SettingsWidget`, `TelegramCard` |
| `help_popup.py` | 도움말 팝업 | `HelpPopup` |
| `help_widget.py` | 도움말 위젯 | `HelpWidget` |
| `telegram_popup.py` | 텔레그램 설정 | `TelegramPopup` |

### 🔐 로그인 및 라이선스
| 파일 | 용도 | 주요 클래스 |
|------|------|------------|
| `login_dialog.py` | 로그인 | `LoginDialog` |
| `pc_license_dialog.py` | PC 라이선스 | `PCLicenseDialog` |
| `payment_dialog.py` | 결제 UI | `PaymentDialog` |
| `tier_popup.py` | 등급 안내 | `TierPopup` |

### 💹 매매 관련
| 파일 | 용도 | 주요 클래스 |
|------|------|------------|
| `single_trade_widget.py` | 단일 매매 | `SingleTradeWidget` |
| `multi_trade_widget.py` | 다중 매매 | `MultiTradeWidget` |
| `position_widget.py` | 포지션 표시 | `PositionWidget` |
| `history_widget.py` | 거래 내역 | `HistoryWidget` |
| `auto_pipeline_widget.py` | 자동 파이프라인 | `AutoPipelineWidget` |

### 🔔 알림
| 파일 | 용도 | 주요 클래스 |
|------|------|------------|
| `notification_manager.py` | 알림 관리 | `NotificationManager` |
| `notification_widget.py` | 알림 설정 | `NotificationWidget` |
| `telegram_settings_widget.py` | 텔레그램 설정 | `TelegramSettingsWidget` |

---

## 🔌 Exchanges 모듈 (거래소 연동)

### 거래소 어댑터
| 파일 | 거래소 | 유형 | 특징 |
|------|--------|------|------|
| `bybit_exchange.py` | Bybit | 선물 | 메인 거래소 |
| `binance_exchange.py` | Binance | 선물 | 글로벌 최대 |
| `okx_exchange.py` | OKX | 선물 | passphrase 필요 |
| `bitget_exchange.py` | Bitget | 선물 | USDT-M |
| `bingx_exchange.py` | BingX | 선물 | 영구 선물 |
| `upbit_exchange.py` | 업비트 | 현물 | 원화 마켓 |
| `bithumb_exchange.py` | 빗썸 | 현물 | 원화 마켓 |

### 공통 모듈
| 파일 | 용도 |
|------|------|
| `base_exchange.py` | 거래소 추상 클래스 |
| `exchange_manager.py` | 통합 거래소 관리 |
| `ccxt_exchange.py` | CCXT 범용 어댑터 |
| `ws_handler.py` | WebSocket 핸들러 |

---

## 🛠️ Utils 모듈 (유틸리티)

### 데이터 처리
| 파일 | 용도 |
|------|------|
| `data_utils.py` | 데이터 리샘플링 |
| `data_downloader.py` | 데이터 다운로드 |
| `indicators.py` | 기술적 지표 (RSI, ATR, MACD) |

### 캐시 및 상태
| 파일 | 용도 |
|------|------|
| `cache_manager.py` | 캐시 관리 |
| `cache_cleaner.py` | 캐시 정리 |
| `state_manager.py` | 상태 관리 |
| `preset_manager.py` | 프리셋 관리 |

### 보안 및 API
| 파일 | 용도 |
|------|------|
| `crypto.py` | 암호화 유틸 |
| `api_utils.py` | API 호출 유틸 |
| `retry.py` | 재시도 로직 |

### 기타
| 파일 | 용도 |
|------|------|
| `logger.py` | 로깅 설정 |
| `helpers.py` | 공통 헬퍼 |
| `validators.py` | 유효성 검사 |
| `error_reporter.py` | 에러 리포트 |

---

## 📜 Strategies 모듈 (매매 전략)

| 파일 | 용도 |
|------|------|
| `base_strategy.py` | 전략 기본 클래스 (상속용) |
| `wm_pattern_strategy.py` | W/M 패턴 전략 |
| `parameter_optimizer.py` | 파라미터 최적화 |
| `strategy_loader.py` | 전략 동적 로드 |

---

## 🌐 Web 모듈 (웹 UI)

```
web/
├── frontend/
│   ├── index.html        # Vue.js SPA
│   └── guide_data.js     # 가이드 데이터
├── backend/
│   └── main.py           # FastAPI 서버
└── run_server.py         # 서버 실행
```

---

## 📄 루트 스크립트

### 실행 스크립트
| 파일 | 용도 |
|------|------|
| `run_gui.py` | GUI 실행 |
| `run_batch_full.py` | 배치 실행 |

### 설정 및 경로
| 파일 | 용도 |
|------|------|
| `paths.py` | 경로 관리 (Paths 클래스) |
| `license_tiers.py` | 라이선스 등급 정의 |
| `license_manager.py` | 라이선스 관리 |

### 알림
| 파일 | 용도 |
|------|------|
| `telegram_notifier.py` | 텔레그램 알림 (싱글톤) |
| `notification_manager.py` | 알림 통합 관리 |

### 가이드 및 도움말
| 파일 | 용도 |
|------|------|
| `user_guide.py` | 사용자 가이드 텍스트 |
| `error_guide.py` | 에러 해결 가이드 |

### 유틸리티
| 파일 | 용도 |
|------|------|
| `smc_utils.py` | SMC 유틸리티 |
| `system_doctor.py` | 시스템 진단 |
| `trading_safety.py` | 매매 안전 검사 |

---

## 📊 모듈 통계

| 카테고리 | 파일 수 | 설명 |
|----------|---------|------|
| Core | 30 | 핵심 비즈니스 로직 |
| GUI | 71 | PyQt6 데스크톱 UI |
| Utils | 23 | 유틸리티 함수 |
| Exchanges | 13 | 거래소 어댑터 |
| Strategies | 6 | 매매 전략 |
| Web | 4 | 웹 프론트/백엔드 |
| Root | ~40 | 실행 및 설정 스크립트 |
| **총계** | **~187** | |

---

*다음: [FEATURE_TREE.md](./FEATURE_TREE.md) - 기능 연동 트리*
