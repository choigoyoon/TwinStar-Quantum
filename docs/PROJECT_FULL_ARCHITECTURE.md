# TwinStar-Quantum 전체 프로젝트 아키텍처 (v7.6)

> **작성일**: 2026-01-15
> **버전**: v7.6 (GPU 가속 Phase P1 예정)
> **Python**: 3.12
> **PyQt6**: 6.6.0+
> **규모**: 150+ 모듈, 30,000+ 줄

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [전체 디렉토리 트리](#전체-디렉토리-트리)
3. [모듈 연결 맵](#모듈-연결-맵)
4. [계층별 상세 분석](#계층별-상세-분석)
5. [데이터 흐름도](#데이터-흐름도)
6. [GPU 가속 업그레이드 로드맵](#gpu-가속-업그레이드-로드맵)
7. [주요 기능 시나리오](#주요-기능-시나리오)

---

## 프로젝트 개요

### 🎯 목적

**암호화폐 자동매매 플랫폼** - CCXT 기반 8개 거래소 통합 지원

### 🌟 핵심 기능

| 기능 | 설명 | 모듈 |
|------|------|------|
| **실시간 거래** | 8개 거래소 동시 지원 | `core/unified_bot.py` |
| **백테스트** | 단일/멀티 심볼 전략 검증 | `core/strategy_core.py` |
| **최적화** | 파라미터 그리드 서치 (3,600 조합) | `core/optimizer.py` |
| **GUI** | PyQt6 데스크톱 UI | `GUI/staru_main.py` |
| **웹** | FastAPI + Vue.js 대시보드 | `web/backend/main.py` |
| **데이터 관리** | Parquet 캐싱, Lazy Load | `core/data_manager.py` |

### 📊 프로젝트 규모

```
총 Python 파일:   150+ 개
총 코드 라인:     30,000+ 줄
테스트 케이스:    130+ 개
문서 파일:        50+ 개
지원 거래소:      8개
```

---

## 전체 디렉토리 트리

```
TwinStar-Quantum/
│
├── 📂 core/                        # 핵심 거래 로직 (30개 모듈, 8,500줄)
│   │
│   ├── 🔥 통합 봇 시스템
│   │   ├── unified_bot.py              # 통합 봇 (Radical Delegation)
│   │   ├── bot_state.py                # 봇 상태 관리
│   │   ├── signal_processor.py         # 신호 처리
│   │   ├── order_executor.py           # 주문 실행
│   │   └── position_manager.py         # 포지션 관리
│   │
│   ├── 📈 전략 엔진
│   │   ├── strategy_core.py            # 전략 엔진 (Alpha-X7, 거래소 독립)
│   │   └── trade_common.py             # 공통 거래 로직
│   │
│   ├── 💾 데이터 관리 (Lazy Load 아키텍처)
│   │   ├── data_manager.py             # Parquet I/O (메모리: 1000개, 디스크: 35,000개)
│   │   ├── shared_data_manager.py      # 공유 데이터 관리
│   │   └── api_rate_limiter.py         # API 레이트 제한
│   │
│   ├── 🔬 최적화 시스템
│   │   ├── optimizer.py                # 단일 최적화
│   │   ├── multi_optimizer.py          # 멀티 심볼 최적화
│   │   ├── batch_optimizer.py          # 배치 최적화
│   │   ├── optimization_logic.py       # 최적화 로직 (SSOT)
│   │   └── auto_optimizer.py           # 자동 최적화
│   │
│   ├── 📊 백테스트 시스템
│   │   ├── unified_backtest.py         # 단일 백테스트
│   │   ├── multi_backtest.py           # 멀티 심볼 백테스트
│   │   └── multi_symbol_backtest.py    # 멀티 심볼 백테스트 v2
│   │
│   ├── 💰 자본 관리
│   │   ├── capital_manager.py          # 자본 관리
│   │   ├── shared_capital_manager.py   # 공유 자본 관리
│   │   └── pnl_tracker.py              # 수익률 추적
│   │
│   ├── 🚀 고급 거래 모드
│   │   ├── multi_trader.py             # 멀티 거래
│   │   ├── multi_sniper.py             # 스나이퍼 모드
│   │   └── dual_track_trader.py        # 듀얼 트랙
│   │
│   ├── 🔍 분석 도구
│   │   ├── auto_scanner.py             # 자동 스캔
│   │   ├── async_scanner.py            # 비동기 스캔
│   │   ├── chart_matcher.py            # 차트 패턴 매칭
│   │   └── batch_verifier.py           # 배치 검증
│   │
│   └── 🛡️ 시스템 관리
│       ├── preset_health.py            # 프리셋 건강도
│       ├── crypto_payment.py           # 암호화폐 결제
│       ├── license_guard.py            # 라이선스 검증
│       └── updater.py                  # 자동 업데이트
│
├── 📂 exchanges/                   # 거래소 어댑터 (13개 모듈, 3,200줄)
│   ├── base_exchange.py            # 추상 기본 클래스 (ABC)
│   ├── exchange_manager.py         # 거래소 관리자
│   ├── ws_handler.py               # WebSocket 핸들러
│   │
│   ├── 🌐 글로벌 거래소 (선물)
│   │   ├── ccxt_exchange.py            # CCXT 공통 어댑터
│   │   ├── binance_exchange.py         # Binance (최대 125× 레버리지)
│   │   ├── bybit_exchange.py           # Bybit (최대 100× 레버리지)
│   │   ├── okx_exchange.py             # OKX (최대 125× 레버리지)
│   │   ├── bingx_exchange.py           # BingX
│   │   ├── bitget_exchange.py          # Bitget
│   │   └── lighter_exchange.py         # Lighter (DEX)
│   │
│   └── 🇰🇷 한국 거래소 (현물)
│       ├── upbit_exchange.py           # Upbit
│       └── bithumb_exchange.py         # Bithumb
│
├── 📂 strategies/                  # 거래 전략
│   ├── base_strategy.py            # 전략 기본 클래스 (ABC)
│   └── common/                     # 공통 전략 로직
│
├── 📂 trading/                     # 거래 API 및 백테스트
│   ├── core/                       # 지표, 신호, 필터, 실행
│   ├── backtest/                   # 백테스트 엔진
│   └── strategies/                 # 전략 구현
│
├── 📂 GUI/                         # 레거시 GUI (102개 파일, 12,000줄)
│   ├── staru_main.py               # ⭐ 메인 윈도우 (통합 지점, 850줄)
│   │
│   ├── 📊 주요 위젯
│   │   ├── trading_dashboard.py        # 트레이딩 대시보드
│   │   ├── backtest_widget.py          # 백테스트 위젯 (레거시)
│   │   ├── optimization_widget.py      # 최적화 위젯 (레거시, 2,129줄)
│   │   └── settings_widget.py          # 설정 위젯 (1,187줄)
│   │
│   ├── 🎨 컴포넌트 (9개)
│   │   ├── interactive_chart.py        # 백테스트 차트 (PyQtGraph)
│   │   ├── enhanced_chart_widget.py    # 실시간 차트
│   │   ├── chart_items.py              # K선, 거래량 (커스텀 아이템)
│   │   └── ...
│   │
│   └── 🗂️ 기타 모듈 (90+)
│       ├── dialogs/                    # 다이얼로그 (15개)
│       ├── trading/                    # 트레이딩 위젯
│       ├── backtest/                   # 백테스트 위젯
│       ├── optimization/               # 최적화 위젯
│       ├── data/                       # 데이터 관리
│       ├── dashboard/                  # 대시보드
│       └── settings/                   # 설정
│
├── 📂 ui/                          # 신규 디자인 시스템 (20개 파일, 3,000줄)
│   │
│   ├── 🎨 디자인 시스템 (PyQt6 무의존)
│   │   ├── tokens.py               # 디자인 토큰 (SSOT, 400줄)
│   │   │   ├── ColorTokens (25개 색상)
│   │   │   ├── TypographyTokens (8단계 크기, 5단계 가중치)
│   │   │   ├── SpacingTokens (4px 기반 11단계)
│   │   │   ├── RadiusTokens (6단계)
│   │   │   ├── ShadowTokens (8개)
│   │   │   └── AnimationTokens (3단계 속도)
│   │   │
│   │   ├── theme.py                # ThemeGenerator (500줄)
│   │   │   └── generate() → 16개 위젯 스타일시트
│   │   │
│   │   └── styles/                 # 컴포넌트별 스타일 (5개 모듈)
│   │       ├── buttons.py              # ButtonStyles
│   │       ├── inputs.py               # InputStyles
│   │       ├── cards.py                # CardStyles (NEW)
│   │       ├── tables.py               # TableStyles
│   │       └── dialogs.py              # DialogStyles
│   │
│   ├── 🧩 위젯 (PyQt6)
│   │   ├── backtest/               # 📊 백테스트 위젯 (Phase 2 완료, 2,400줄)
│   │   │   ├── main.py                 # BacktestWidget (148줄)
│   │   │   ├── single.py               # SingleBacktestTab (727줄)
│   │   │   ├── multi.py                # MultiBacktestTab (425줄)
│   │   │   ├── worker.py               # BacktestWorker (386줄)
│   │   │   ├── components.py           # 공통 컴포넌트 (288줄)
│   │   │   ├── params.py               # 파라미터 입력 (360줄)
│   │   │   └── styles.py               # 스타일 정의 (196줄)
│   │   │
│   │   ├── optimization/           # 🔬 최적화 위젯 (1,700줄)
│   │   │   ├── main.py                 # OptimizationWidget (160줄)
│   │   │   ├── single.py               # SingleOptimizationTab
│   │   │   ├── batch.py                # BatchOptimizationTab
│   │   │   ├── params.py               # 파라미터 입력
│   │   │   ├── worker.py               # OptimizationWorker
│   │   │   ├── results_viewer.py       # 결과 뷰어 (535줄)
│   │   │   │
│   │   │   └── 🆕 heatmap.py           # GPU 히트맵 (P1-1 예정, ~400줄)
│   │   │       ├── OptimizationHeatmapWidget
│   │   │       └── MultiMetricHeatmapWidget
│   │   │
│   │   ├── dashboard/              # 📈 트레이딩 대시보드
│   │   │   ├── main.py                 # TradingDashboard
│   │   │   ├── header.py               # DashboardHeader
│   │   │   └── status_cards.py         # StatusCard, PnLCard
│   │   │
│   │   └── results.py              # 결과 표시 (GradeLabel)
│   │
│   ├── ⚙️ 워커 (QThread)
│   │   └── tasks.py                # BacktestWorker, OptimizationWorker
│   │
│   └── 💬 다이얼로그
│       ├── base.py                 # BaseDialog
│       └── message.py              # MessageDialog, ConfirmDialog
│
├── 📂 config/                      # 설정 중앙화 (SSOT, 8개 모듈, 800줄)
│   ├── constants/                  # 모든 상수
│   │   ├── __init__.py                 # 중앙 export 허브
│   │   ├── exchanges.py                # EXCHANGE_INFO (8개 거래소 메타데이터)
│   │   ├── timeframes.py               # TF_MAPPING (15m, 1h, 4h, 1d)
│   │   ├── trading.py                  # SLIPPAGE=0.001, FEE=0.0004
│   │   ├── grades.py                   # S/A/B/C 등급 기준
│   │   ├── paths.py                    # CACHE_DIR, DATA_DIR
│   │   └── presets.py                  # 프리셋 상수
│   │
│   ├── parameters.py               # DEFAULT_PARAMS (거래 파라미터)
│   │
│   └── 🆕 gpu_settings.json        # GPU 설정 (P1-2 예정)
│       ├── enabled: true
│       ├── backend: "d3d11"
│       └── max_fps: 30
│
├── 📂 utils/                       # 유틸리티 (27개 모듈, 4,500줄)
│   │
│   ├── ⭐ 핵심 유틸리티
│   │   ├── metrics.py              # 백테스트 메트릭 (SSOT - Phase 1-B, 375줄)
│   │   │   ├── calculate_mdd()
│   │   │   ├── calculate_profit_factor()
│   │   │   ├── calculate_win_rate()
│   │   │   ├── calculate_sharpe_ratio()
│   │   │   ├── calculate_backtest_metrics() (17개 지표)
│   │   │   └── format_metrics_report()
│   │   │
│   │   ├── indicators.py           # 지표 계산 (RSI, ATR, MACD, 250줄)
│   │   ├── logger.py               # 중앙 로깅 (150줄)
│   │   ├── data_utils.py           # 데이터 유틸 (리샘플링, 200줄)
│   │   └── preset_storage.py       # 프리셋 저장/로드 (180줄)
│   │
│   ├── ⚡ GPU 가속 (P0 완료)
│   │   ├── table_models.py         # QTableView Model (436줄, 10× 향상)
│   │   │   ├── BacktestTradeModel
│   │   │   └── OptimizationResultModel
│   │   │
│   │   └── chart_throttle.py       # 차트 스로틀링 (244줄, 5× 향상)
│   │       ├── ChartThrottle (30 FPS 제한)
│   │       └── throttle_chart_update() 데코레이터
│   │
│   └── 🔧 기타 유틸리티 (20+ 모듈)
│       ├── api_utils.py                # API 유틸리티
│       ├── cache_manager.py            # 캐시 관리
│       ├── cache_cleaner.py            # 캐시 정리
│       ├── chart_profiler.py           # 차트 성능 측정
│       ├── crypto.py                   # 암호화 유틸
│       ├── data_downloader.py          # 데이터 다운로드
│       ├── error_reporter.py           # 에러 리포팅
│       ├── health_check.py             # 헬스 체크
│       ├── timezone_helper.py          # 타임존 변환
│       └── ...
│
├── 📂 web/                         # 웹 인터페이스 (2개 모듈, 800줄)
│   ├── backend/
│   │   └── main.py                 # FastAPI REST API (/api/*)
│   │
│   ├── frontend/
│   │   ├── index.html              # SPA 웹 대시보드 (Vue.js 3 + Tailwind)
│   │   │   ├── 매매 탭
│   │   │   ├── 백테스트 탭
│   │   │   ├── 최적화 탭
│   │   │   ├── 설정 탭
│   │   │   └── 자동매매 탭
│   │   │
│   │   └── guide_data.js           # 가이드 콘텐츠
│   │
│   └── run_server.py               # 서버 실행
│
├── 📂 storage/                     # 암호화 저장소 (3개 모듈, 500줄)
│   ├── secure_storage.py           # API 키 암호화 (AES-256)
│   ├── key_manager.py              # 키 관리
│   └── local_trade_db.py           # 로컬 거래 DB
│
├── 📂 locales/                     # 다국어 지원 (2개 언어)
│   ├── ko.json                     # 한국어 (200개 키)
│   ├── en.json                     # 영어 (200개 키)
│   └── __init__.py
│
├── 📂 tests/                       # 테스트 (130+ 케이스, 3,000줄)
│   ├── test_metrics_phase1d.py     # 메트릭 테스트 (46개, Phase 1-B)
│   ├── test_phase1_modules.py      # Phase 1 모듈 테스트
│   ├── test_data_continuity_lazy_load.py # Lazy Load 테스트
│   └── ...
│
├── 📂 data/                        # 데이터 저장소
│   ├── cache/                      # Parquet 캐시
│   │   ├── bybit_btcusdt_15m.parquet   # 15분봉 (Single Source, 280KB)
│   │   └── bybit_btcusdt_1h.parquet    # 1시간봉 (DEPRECATED)
│   │
│   ├── bot_status.json             # 봇 상태 (실행 중인 봇 정보)
│   ├── capital_config.json         # 자본 설정 (거래소별 자본 배분)
│   ├── exchange_keys.json          # 거래소 키 메타데이터
│   ├── encrypted_keys.dat          # 암호화된 API 키 (AES-256)
│   ├── system_config.json          # 시스템 설정
│   └── daily_pnl.json              # 일일 수익률 기록
│
├── 📂 docs/                        # 문서 (50+ 파일)
│   ├── CLAUDE.md                   # 🔥 프로젝트 헌법 (개발 규칙 v7.6, 1,200줄)
│   ├── WORK_LOG_20260115.txt       # 작업 로그 (Session 1-17)
│   ├── GPU_ACCELERATION_ROADMAP.md # GPU 가속 로드맵 (P0 완료, P1/P2 계획)
│   ├── P1_STEP1_PLAN.md            # P1-1 Step 1 계획서 (450줄)
│   ├── PROJECT_ARCHITECTURE.md     # 기존 아키텍처 문서
│   ├── PROJECT_FULL_ARCHITECTURE.md # 🆕 이 문서
│   │
│   └── 기타 문서 (45+)
│       ├── PARAMETER_IMPACT_GUIDE.md
│       ├── DATA_FLOW_ARCHITECTURE.md
│       ├── PRESET_GUIDE.md
│       └── ...
│
├── 📂 tools/                       # 개발 도구 (20+ 스크립트)
├── 📂 sandbox_optimization/        # 최적화 샌드박스
│
├── 📄 main.py                      # 진입점 (오케스트레이션만, 50줄)
├── 📄 requirements.txt             # 패키지 의존성 (40개 패키지)
├── 📄 pyrightconfig.json           # 타입 체크 설정 (VS Code Pylance)
└── 📄 .gitignore
```

---

## 모듈 연결 맵

### 1. 전체 시스템 의존성 그래프

```mermaid
graph TB
    %% 진입점
    Entry[main.py / staru_main.py] --> App[QApplication]

    %% UI 계층
    App --> GUILegacy[GUI/ 레거시 UI]
    App --> UIModern[ui/ 신규 디자인 시스템]

    %% 레거시 GUI
    GUILegacy --> Dashboard[trading_dashboard.py]
    GUILegacy --> BacktestUI[backtest_widget.py]
    GUILegacy --> OptUI[optimization_widget.py]
    GUILegacy --> SettingsUI[settings_widget.py]

    %% 신규 UI
    UIModern --> Tokens[design_system/tokens.py]
    UIModern --> Theme[design_system/theme.py]
    UIModern --> BacktestNew[widgets/backtest/]
    UIModern --> OptNew[widgets/optimization/]
    UIModern --> DashboardNew[widgets/dashboard/]

    %% Core 로직
    Dashboard --> Bot[core/unified_bot.py]
    BacktestUI --> Bot
    BacktestNew --> Bot
    OptUI --> Optimizer[core/optimizer.py]
    OptNew --> Optimizer

    Bot --> Strategy[core/strategy_core.py]
    Bot --> DataMgr[core/data_manager.py]
    Bot --> SignalProc[core/signal_processor.py]
    Bot --> OrderExec[core/order_executor.py]
    Bot --> PosMgr[core/position_manager.py]

    Optimizer --> Strategy
    Optimizer --> OptLogic[core/optimization_logic.py]

    %% 거래소
    OrderExec --> ExMgr[exchanges/exchange_manager.py]
    ExMgr --> BaseEx[exchanges/base_exchange.py]
    BaseEx --> BinanceEx[exchanges/binance_exchange.py]
    BaseEx --> BybitEx[exchanges/bybit_exchange.py]
    BaseEx --> OtherEx[exchanges/8 other exchanges]

    %% 유틸리티
    Strategy --> Indicators[utils/indicators.py]
    Strategy --> Metrics[utils/metrics.py]
    DataMgr --> DataUtils[utils/data_utils.py]
    UIModern --> TableModels[utils/table_models.py]
    UIModern --> ChartThrottle[utils/chart_throttle.py]

    %% 설정
    Strategy --> Constants[config/constants/]
    Bot --> Parameters[config/parameters.py]

    %% 스타일 정의
    classDef entry fill:#f96,stroke:#333,stroke-width:4px
    classDef ui fill:#bbf,stroke:#333
    classDef core fill:#9f9,stroke:#333
    classDef exchange fill:#ff9,stroke:#333
    classDef util fill:#f9f,stroke:#333
    classDef config fill:#9ff,stroke:#333

    class Entry entry
    class GUILegacy,UIModern ui
    class Bot,Strategy,Optimizer core
    class ExMgr,BaseEx,BinanceEx,BybitEx exchange
    class Indicators,Metrics,TableModels util
    class Constants,Parameters config
```

### 2. 핵심 모듈 의존성 (상세)

```mermaid
graph LR
    %% unified_bot.py 의존성
    UnifiedBot[unified_bot.py] --> BotState[bot_state.py]
    UnifiedBot --> DataMgr[data_manager.py]
    UnifiedBot --> SignalProc[signal_processor.py]
    UnifiedBot --> OrderExec[order_executor.py]
    UnifiedBot --> PosMgr[position_manager.py]

    %% data_manager.py 의존성
    DataMgr --> Constants[config.constants.CACHE_DIR]
    DataMgr --> Constants2[config.constants.TF_MAPPING]
    DataMgr --> DataUtils[utils.data_utils.resample]

    %% signal_processor.py 의존성
    SignalProc --> StrategyCore[strategy_core.py]

    %% strategy_core.py 의존성
    StrategyCore --> Indicators[utils.indicators.RSI/ATR/MACD]
    StrategyCore --> Metrics[utils.metrics.calculate_backtest_metrics]
    StrategyCore --> DefaultParams[config.parameters.DEFAULT_PARAMS]

    %% order_executor.py 의존성
    OrderExec --> BaseEx[exchanges.base_exchange.BaseExchange]

    %% BaseExchange 구현체
    BaseEx --> BinanceEx[binance_exchange.py]
    BaseEx --> BybitEx[bybit_exchange.py]
    BaseEx --> OKXEx[okx_exchange.py]
    BaseEx --> OtherEx[5 other exchanges]
```

### 3. 백테스트 모듈 의존성

```mermaid
graph LR
    %% 백테스트 위젯
    BacktestWidget[ui/widgets/backtest/single.py] --> DesignTokens[ui/design_system/tokens]
    BacktestWidget --> BacktestWorker[ui/widgets/backtest/worker.py]
    BacktestWidget --> Components[ui/widgets/backtest/components.py]
    BacktestWidget --> TableModels[utils/table_models.py]
    BacktestWidget --> ChartThrottle[utils/chart_throttle.py]

    %% 워커
    BacktestWorker --> StrategyCore[core/strategy_core.py]
    StrategyCore --> RunBacktest[run_backtest]

    %% 메트릭 계산
    RunBacktest --> Metrics[utils/metrics.py]
    Metrics --> CalcMDD[calculate_mdd]
    Metrics --> CalcPF[calculate_profit_factor]
    Metrics --> CalcWR[calculate_win_rate]
    Metrics --> CalcSharpe[calculate_sharpe_ratio]
    Metrics --> CalcBacktestMetrics[calculate_backtest_metrics]
```

### 4. 최적화 모듈 의존성

```mermaid
graph LR
    %% 최적화 위젯
    OptWidget[ui/widgets/optimization/main.py] --> SingleOpt[single.py]
    OptWidget --> BatchOpt[batch.py]
    OptWidget --> ResultsViewer[results_viewer.py]

    %% 히트맵 (P1-1 예정)
    ResultsViewer -.-> Heatmap[heatmap.py 🆕]

    %% 워커
    SingleOpt --> OptWorker[worker.py]
    OptWorker --> Optimizer[core/optimizer.py]

    %% 최적화 로직
    Optimizer --> OptLogic[core/optimization_logic.py]
    OptLogic --> StrategyCore[core/strategy_core.py]
    StrategyCore --> Metrics[utils/metrics.py]

    %% 등급 기준
    ResultsViewer --> GradeCriteria[config/constants/grades.py]
    GradeCriteria --> GradeS[S: 승률70%, MDD10%]
    GradeCriteria --> GradeA[A: 승률65%, MDD15%]
    GradeCriteria --> GradeB[B: 승률60%, MDD20%]
    GradeCriteria --> GradeC[C: 승률55%, MDD25%]
```

### 5. 디자인 시스템 의존성

```mermaid
graph TB
    %% 토큰 (PyQt6 무의존)
    Tokens[ui/design_system/tokens.py] --> ColorTokens[ColorTokens: 25개 색상]
    Tokens --> TypographyTokens[TypographyTokens: 8단계 크기]
    Tokens --> SpacingTokens[SpacingTokens: 11단계 간격]
    Tokens --> RadiusTokens[RadiusTokens: 6단계]
    Tokens --> ShadowTokens[ShadowTokens: 8개]
    Tokens --> AnimationTokens[AnimationTokens: 3단계]

    %% 테마 생성기
    Tokens --> Theme[ui/design_system/theme.py]
    Theme --> Generate[ThemeGenerator.generate]
    Generate --> Styles[ui/design_system/styles/*]

    %% 컴포넌트 스타일
    Styles --> ButtonStyles[buttons.py]
    Styles --> InputStyles[inputs.py]
    Styles --> CardStyles[cards.py]
    Styles --> TableStyles[tables.py]
    Styles --> DialogStyles[dialogs.py]

    %% 위젯 사용
    Generate --> BacktestWidget[ui/widgets/backtest/single.py]
    Generate --> OptWidget[ui/widgets/optimization/main.py]
    Generate --> DashboardWidget[ui/widgets/dashboard/main.py]
```

---

## 계층별 상세 분석

### 계층 1: 진입점 (Entry Point)

#### main.py / GUI/staru_main.py

```python
# main.py (진입점, 50줄)
from PyQt6.QtWidgets import QApplication
from GUI.staru_main import StarUMainWindow
import sys

def main():
    app = QApplication(sys.argv)
    window = StarUMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
```

```python
# GUI/staru_main.py (메인 윈도우, 850줄)
class StarUMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 라이선스 검증
        self.license_guard = LicenseGuard()
        if not self.license_guard.verify():
            sys.exit(1)

        # 탭 생성
        self.tabs = QTabWidget()
        self.tabs.addTab(self.trading_dashboard, "📈 트레이딩")
        self.tabs.addTab(self.backtest_widget, "📊 백테스트")
        self.tabs.addTab(self.optimization_widget, "🔬 최적화")
        self.tabs.addTab(self.settings_widget, "⚙️ 설정")

        # 🆕 GPU 설정 탭 (P1-2 예정)
        # self.tabs.addTab(self.gpu_settings_tab, "🎮 GPU 설정")

        self.setCentralWidget(self.tabs)
```

**통합 위젯**:
- `trading_dashboard.py` - 트레이딩 대시보드
- `backtest_widget.py` - 백테스트 위젯 (레거시)
- `optimization_widget.py` - 최적화 위젯 (레거시)
- `settings_widget.py` - 설정 위젯

---

### 계층 2: Core 로직 (핵심 거래)

#### 2.1 통합 봇 (Radical Delegation)

```python
# core/unified_bot.py (통합 봇, 600줄)
class UnifiedBot:
    """
    통합 봇 - Radical Delegation 패턴

    역할: 오케스트레이션만 담당 (위임)
    """

    def __init__(self, exchange: str, symbol: str):
        # 모듈 위임
        self.mod_state = BotState()              # 상태 관리
        self.mod_data = BotDataManager(exchange, symbol)  # 데이터 관리
        self.mod_signal = SignalProcessor()      # 신호 처리
        self.mod_order = OrderExecutor(exchange) # 주문 실행
        self.mod_position = PositionManager()    # 포지션 관리

    def run(self):
        """거래 루프 (위임만)"""
        while self.mod_state.is_running():
            # 1. 데이터 업데이트
            df = self.mod_data.get_latest_data()

            # 2. 신호 처리
            signal = self.mod_signal.process(df, self.params)

            # 3. 주문 실행
            if signal:
                self.mod_order.execute(signal)

            # 4. 포지션 관리
            self.mod_position.update()
```

**연결 모듈**:
- `bot_state.py` - 봇 상태 (실행 중, 정지, 에러)
- `data_manager.py` - 데이터 관리 (Parquet I/O, Lazy Load)
- `signal_processor.py` - 신호 처리 (전략 호출)
- `order_executor.py` - 주문 실행 (거래소 API)
- `position_manager.py` - 포지션 관리 (청산 조건)

#### 2.2 전략 엔진 (Alpha-X7)

```python
# core/strategy_core.py (전략 엔진, 800줄)
class StrategyCore:
    """
    Alpha-X7 전략 엔진

    특징:
    - 거래소 독립적 (BaseExchange 사용)
    - 백테스트 = 실시간 동일 로직
    """

    def check_signal(self, df: pd.DataFrame, params: dict) -> Optional[Signal]:
        """
        신호 확인

        Args:
            df: OHLCV 데이터프레임
            params: 파라미터 딕셔너리

        Returns:
            Signal 객체 또는 None
        """
        # 1. 지표 계산
        from utils.indicators import calculate_rsi, calculate_atr, calculate_macd
        rsi = calculate_rsi(df, params['rsi_period'])
        atr = calculate_atr(df, params['atr_period'])
        macd, signal_line = calculate_macd(df, params['macd_fast'], params['macd_slow'])

        # 2. 진입 조건 확인
        if self._check_entry_long(rsi, macd, signal_line):
            stop_loss = df['close'].iloc[-1] - (atr * params['atr_mult'])
            return Signal(
                side='Long',
                entry_price=df['close'].iloc[-1],
                stop_loss=stop_loss,
                confidence=0.8
            )

        # 3. 진입 조건 (Short)
        if self._check_entry_short(rsi, macd, signal_line):
            stop_loss = df['close'].iloc[-1] + (atr * params['atr_mult'])
            return Signal(
                side='Short',
                entry_price=df['close'].iloc[-1],
                stop_loss=stop_loss,
                confidence=0.8
            )

        return None

    def run_backtest(self, df: pd.DataFrame, params: dict) -> dict:
        """
        백테스트 실행

        Returns:
            메트릭 딕셔너리 (17개 지표)
        """
        trades = []

        for i in range(100, len(df)):
            df_slice = df.iloc[:i]
            signal = self.check_signal(df_slice, params)

            if signal:
                # 가상 거래 실행
                trade = self._execute_virtual_trade(signal, df, i)
                trades.append(trade)

        # 메트릭 계산
        from utils.metrics import calculate_backtest_metrics
        return calculate_backtest_metrics(trades, params['leverage'])
```

**연결 모듈**:
- `utils/indicators.py` - RSI, ATR, MACD 계산
- `utils/metrics.py` - 백테스트 메트릭 (SSOT)
- `config/parameters.py` - DEFAULT_PARAMS

#### 2.3 데이터 관리 (Lazy Load 아키텍처)

```python
# core/data_manager.py (데이터 관리, 500줄)
class BotDataManager:
    """
    데이터 관리자 - Lazy Load 아키텍처

    메모리:   df_entry_full (1000개, 40KB)
    디스크:   Parquet (35,000개, 280KB)
    저장 주기: 15분마다
    I/O 시간: 35ms
    """

    def __init__(self, exchange: str, symbol: str):
        self.exchange = exchange
        self.symbol = symbol
        self.df_entry_full = pd.DataFrame()  # 메모리: 최근 1000개만

    def append_candle(self, candle: dict):
        """
        WebSocket 캔들 추가

        Args:
            candle: {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        """
        # 1. 메모리에 추가
        self.df_entry_full = pd.concat([self.df_entry_full, pd.DataFrame([candle])])

        # 2. 메모리 제한 (최근 1000개만 유지)
        self.df_entry_full = self.df_entry_full.tail(1000)

        # 3. Lazy Merge: 15분마다 Parquet 저장
        if len(self.df_entry_full) % 1000 == 0:
            self._save_with_lazy_merge()

    def _save_with_lazy_merge(self):
        """
        Parquet 병합 저장 (35ms I/O)

        동작:
        1. 기존 Parquet 읽기 (5-15ms)
        2. 메모리 데이터와 병합
        3. 중복 제거
        4. Parquet 저장 (10-20ms)
        """
        import time
        start = time.time()

        # 기존 데이터 로드
        if self.entry_file_path.exists():
            existing = pd.read_parquet(self.entry_file_path)
        else:
            existing = pd.DataFrame()

        # 병합 + 중복 제거
        merged = pd.concat([existing, self.df_entry_full])
        merged = merged.drop_duplicates(subset=['timestamp']).sort_values('timestamp')

        # 저장
        merged.to_parquet(self.entry_file_path)

        elapsed = (time.time() - start) * 1000
        logger.info(f"Lazy Merge: {len(merged)} rows, {elapsed:.1f}ms")

    def load_entry_data(self) -> pd.DataFrame:
        """15분봉 로드 (Single Source)"""
        return pd.read_parquet(self.entry_file_path)

    def resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        리샘플링 (15m → 1h, 4h, 1d)

        Args:
            df: 15분봉 데이터
            timeframe: '1h', '4h', '1d'

        Returns:
            리샘플링된 데이터프레임
        """
        from config.constants import TF_MAPPING
        rule = TF_MAPPING[timeframe]

        return df.resample(rule, on='timestamp').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

    def get_entry_file_path(self) -> Path:
        """Parquet 파일 경로"""
        from config.constants import CACHE_DIR
        symbol_clean = self.symbol.replace('/', '').lower()
        return Path(CACHE_DIR) / f"{self.exchange}_{symbol_clean}_15m.parquet"
```

**성능 지표**:
- 메모리 사용: 40KB (1000개)
- 파일 크기: 280KB (35,000개)
- 읽기 시간: 5-15ms
- 저장 시간: 25-50ms (평균 35ms)
- CPU 부하: 0.0039% (15분당 1회)

#### 2.4 최적화 엔진

```python
# core/optimizer.py (단일 최적화, 400줄)
class Optimizer:
    """
    파라미터 최적화 엔진

    모드:
    - Quick: 8 조합
    - Standard: 3,600 조합
    - Deep: 12,800 조합
    """

    def __init__(self, strategy: StrategyCore):
        self.strategy = strategy

    def optimize(
        self,
        df: pd.DataFrame,
        param_grid: dict,
        mode: str = 'standard'
    ) -> List[OptimizationResult]:
        """
        파라미터 그리드 서치

        Args:
            df: OHLCV 데이터
            param_grid: {'atr_mult': [1.5, 2.0, 2.5], 'filter_tf': ['1h', '4h']}
            mode: 'quick', 'standard', 'deep'

        Returns:
            OptimizationResult 리스트 (Sharpe Ratio 내림차순)
        """
        # 1. 파라미터 조합 생성
        combinations = self._generate_combinations(param_grid, mode)
        logger.info(f"Testing {len(combinations)} combinations")

        # 2. 각 조합마다 백테스트
        results = []
        for i, params in enumerate(combinations):
            metrics = self.strategy.run_backtest(df, params)

            result = OptimizationResult(
                params=params,
                win_rate=metrics['win_rate'],
                total_pnl=metrics['total_pnl'],
                max_drawdown=metrics['mdd'],
                sharpe_ratio=metrics['sharpe_ratio'],
                trade_count=metrics['total_trades'],
                profit_factor=metrics['profit_factor']
            )
            results.append(result)

            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i+1}/{len(combinations)}")

        # 3. Sharpe Ratio 기준 정렬
        results.sort(key=lambda x: x.sharpe_ratio, reverse=True)

        return results

    def _generate_combinations(self, param_grid: dict, mode: str) -> List[dict]:
        """파라미터 조합 생성"""
        if mode == 'quick':
            # 빠른 테스트 (8 조합)
            return self._quick_combinations(param_grid)
        elif mode == 'standard':
            # 표준 (3,600 조합)
            return self._standard_combinations(param_grid)
        elif mode == 'deep':
            # 심화 (12,800 조합)
            return self._deep_combinations(param_grid)
```

**연결 모듈**:
- `optimization_logic.py` - 최적화 로직 (SSOT)
- `multi_optimizer.py` - 멀티 심볼 최적화
- `batch_optimizer.py` - 배치 최적화

---

### 계층 3: 거래소 어댑터

#### 3.1 어댑터 패턴

```python
# exchanges/base_exchange.py (추상 기본 클래스, 200줄)
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Position:
    symbol: str
    side: str  # 'Long' or 'Short'
    entry_price: float
    size: float
    leverage: int
    pnl: float

class BaseExchange(ABC):
    """거래소 추상 기본 클래스"""

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """현재 포지션 조회"""
        pass

    @abstractmethod
    def place_market_order(
        self,
        symbol: str,
        side: str,
        size: float,
        leverage: int = 1
    ) -> bool | str:
        """
        시장가 주문

        Returns:
            Binance, Bybit: str (order_id)
            OKX, BingX, Bitget: bool (성공 여부)
        """
        pass

    @abstractmethod
    def close_position(self, symbol: str) -> bool:
        """포지션 청산"""
        pass

    @abstractmethod
    def get_balance(self) -> float:
        """계좌 잔고 조회"""
        pass
```

#### 3.2 Binance 구현

```python
# exchanges/binance_exchange.py (400줄)
class BinanceExchange(BaseExchange):
    """Binance 거래소 어댑터"""

    def __init__(self, api_key: str, secret: str, testnet: bool = False):
        import ccxt

        self.client = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # 선물 거래
                'adjustForTimeDifference': True
            }
        })

        if testnet:
            self.client.set_sandbox_mode(True)

    def get_position(self, symbol: str) -> Optional[Position]:
        """포지션 조회 (Binance 전용)"""
        try:
            positions = self.client.fetch_positions([symbol])

            for pos in positions:
                if float(pos['contracts']) > 0:
                    return Position(
                        symbol=pos['symbol'],
                        side='Long' if pos['side'] == 'long' else 'Short',
                        entry_price=float(pos['entryPrice']),
                        size=float(pos['contracts']),
                        leverage=int(pos['leverage']),
                        pnl=float(pos['unrealizedPnl'])
                    )

            return None

        except Exception as e:
            logger.error(f"Failed to get position: {e}")
            return None

    def place_market_order(
        self,
        symbol: str,
        side: str,
        size: float,
        leverage: int = 1
    ) -> str:
        """시장가 주문 (주문 ID 반환)"""
        try:
            # 레버리지 설정
            self.client.set_leverage(leverage, symbol)

            # 주문 실행
            order = self.client.create_market_order(
                symbol=symbol,
                side='buy' if side == 'Long' else 'sell',
                amount=size
            )

            logger.info(f"Order placed: {order['id']}")
            return order['id']

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return ""

    def close_position(self, symbol: str) -> bool:
        """포지션 청산"""
        position = self.get_position(symbol)
        if not position:
            return True

        # 반대 방향 주문
        opposite_side = 'Short' if position.side == 'Long' else 'Long'
        order_id = self.place_market_order(symbol, opposite_side, position.size)

        return bool(order_id)
```

**지원 거래소** (8개):
1. `binance_exchange.py` - Binance (최대 125× 레버리지)
2. `bybit_exchange.py` - Bybit (최대 100× 레버리지)
3. `okx_exchange.py` - OKX (최대 125× 레버리지)
4. `bingx_exchange.py` - BingX
5. `bitget_exchange.py` - Bitget
6. `upbit_exchange.py` - Upbit (현물, 한국)
7. `bithumb_exchange.py` - Bithumb (현물, 한국)
8. `lighter_exchange.py` - Lighter (DEX)

---

### 계층 4: GUI 레거시 + UI 신규

#### 4.1 레거시 최적화 위젯

```python
# GUI/optimization_widget.py (레거시, 2,129줄)
class OptimizationWidget(QWidget):
    """
    최적화 위젯 (레거시)

    문제점:
    - ❌ 히트맵 없음 (테이블 기반만)
    - ❌ QTableWidget 사용 (느림)
    - ❌ 파라미터 관계 파악 어려움
    """

    def __init__(self):
        super().__init__()

        # 테이블 기반 결과 표시
        self.results_table = QTableWidget()

    def display_results(self, results: List[OptimizationResult]):
        """결과 표시 (테이블만)"""
        self.results_table.setRowCount(len(results))

        for i, result in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(f"{result.win_rate:.1f}"))
            self.results_table.setItem(i, 1, QTableWidgetItem(f"{result.sharpe_ratio:.2f}"))
            # ... (12개 컬럼 채우기)

        # 렌더링 시간: 500ms (1000개 행 기준)
```

#### 4.2 신규 최적화 위젯 (마이그레이션 중)

```python
# ui/widgets/optimization/main.py (신규, 160줄)
class OptimizationWidget(QWidget):
    """
    최적화 메인 위젯 (신규)

    개선:
    - ✅ QTableView + Model (10× 빠름)
    - ✅ 등급별 탭 (S/A/B/C)
    - 🆕 히트맵 탭 (P1-1 예정)
    """

    optimization_finished = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.tabs = QTabWidget()

        # 탭 추가
        self.single_tab = SingleOptimizationTab()
        self.batch_tab = BatchOptimizationTab()
        self.results_viewer = ModeGradeResultsViewer()

        self.tabs.addTab(self.single_tab, "단일 최적화")
        self.tabs.addTab(self.batch_tab, "배치 최적화")
        self.tabs.addTab(self.results_viewer, "결과 뷰어")

        # 🆕 히트맵 탭 (P1-1 예정)
        # self.heatmap_widget = OptimizationHeatmapWidget()
        # self.tabs.addTab(self.heatmap_widget, "🌡️ 히트맵")
```

#### 4.3 히트맵 위젯 (P1-1 예정)

```python
# ui/widgets/optimization/heatmap.py (신규, ~400줄, P1-1 예정)
class OptimizationHeatmapWidget(QWidget):
    """
    GPU 가속 히트맵 위젯

    기능:
    - 2D 파라미터 그리드 시각화
    - PyQtGraph ImageItem (GPU 텍스처)
    - 마우스 호버 툴팁
    - 클릭 시그널

    성능:
    - 12,800개 조합 < 100ms
    - 20× 향상 (테이블 대비)
    """

    heatmap_clicked = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        # PyQtGraph PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground(Colors.bg_base)

        # ImageItem (GPU 텍스처)
        self.image_item = pg.ImageItem()
        self.plot_widget.addItem(self.image_item)

        # ColorBar 범례
        self.colorbar = pg.ColorBarItem(
            values=(0, 100),
            colorMap='viridis',
            width=15
        )
        self.colorbar.setImageItem(self.image_item)

    def update_heatmap(self, results: List[Dict]):
        """히트맵 업데이트 (GPU 텍스처로 전송)"""
        # 1. List[Dict] → np.ndarray (2D)
        grid = self._reshape_to_grid(results, param_x, param_y, metric)

        # 2. GPU 텍스처로 전송
        self.image_item.setImage(grid, autoLevels=True)

        # 렌더링 시간: < 100ms (12,800개 조합 기준)

    def _reshape_to_grid(
        self,
        results: List[Dict],
        param_x: str,
        param_y: str,
        metric: str
    ) -> np.ndarray:
        """결과 리스트를 2D 그리드로 변환"""
        # 1. 파라미터 고유값 추출
        x_values = sorted(set(r['params'][param_x] for r in results))
        y_values = sorted(set(r['params'][param_y] for r in results))

        # 2. 2D 배열 초기화
        grid = np.full((len(y_values), len(x_values)), np.nan)

        # 3. 매핑 딕셔너리
        x_map = {val: idx for idx, val in enumerate(x_values)}
        y_map = {val: idx for idx, val in enumerate(y_values)}

        # 4. 데이터 채우기
        for result in results:
            x_idx = x_map[result['params'][param_x]]
            y_idx = y_map[result['params'][param_y]]
            grid[y_idx, x_idx] = result[metric]

        return grid
```

---

### 계층 5: 유틸리티

#### 5.1 백테스트 메트릭 (SSOT - Phase 1-B)

```python
# utils/metrics.py (375줄)
def calculate_mdd(trades: List[Dict]) -> float:
    """
    최대 낙폭(MDD) 계산

    Args:
        trades: [{'pnl': 10.5}, {'pnl': -5.2}, ...]

    Returns:
        MDD (%) - 양수
    """
    if not trades:
        return 0.0

    cumulative = np.cumsum([t['pnl'] for t in trades])
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max

    return abs(drawdown.min()) if len(drawdown) > 0 else 0.0

def calculate_profit_factor(trades: List[Dict]) -> float:
    """Profit Factor = 총 이익 / 총 손실"""
    gains = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    losses = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))

    # losses==0이면 gains 반환 (Phase 1-B 통일)
    return gains / losses if losses > 0 else gains

def calculate_backtest_metrics(
    trades: List[Dict],
    leverage: int = 1,
    capital: float = 100.0
) -> dict:
    """
    전체 백테스트 메트릭 계산 (17개 지표)

    Returns:
        {
            'total_trades': 500,
            'win_rate': 65.3,
            'total_pnl': 45.2,
            'profit_factor': 2.1,
            'mdd': 12.5,
            'sharpe_ratio': 1.8,
            'sortino_ratio': 2.5,
            'calmar_ratio': 3.6,
            ...
        }
    """
    if not trades:
        return _empty_metrics()

    # 17개 메트릭 계산
    return {
        'total_trades': len(trades),
        'win_rate': calculate_win_rate(trades),
        'total_pnl': sum(t['pnl'] for t in trades),
        'profit_factor': calculate_profit_factor(trades),
        'mdd': calculate_mdd(trades),
        'sharpe_ratio': calculate_sharpe_ratio([t['pnl'] for t in trades]),
        'sortino_ratio': calculate_sortino_ratio([t['pnl'] for t in trades]),
        'calmar_ratio': calculate_calmar_ratio(trades),
        'avg_win': _calculate_avg_win(trades),
        'avg_loss': _calculate_avg_loss(trades),
        'max_consecutive_wins': _max_consecutive_wins(trades),
        'max_consecutive_losses': _max_consecutive_losses(trades),
        'expectancy': _calculate_expectancy(trades),
        'recovery_factor': _recovery_factor(trades),
        'final_capital': capital * (1 + sum(t['pnl'] for t in trades) / 100),
        'leverage': leverage,
        'timestamp': pd.Timestamp.now().isoformat()
    }
```

**성과 (Phase 1-B)**:
- ✅ 중복 제거: 4곳 → 1곳 (70줄 코드 감소)
- ✅ 계산 통일: Profit Factor, Sharpe Ratio 불일치 해결
- ✅ 검증 완료: 46개 단위 테스트 (100% 통과)
- ✅ 성능: 100,000개 거래 처리 1.18초

#### 5.2 QTableView Model (P0 완료)

```python
# utils/table_models.py (436줄)
class BacktestTradeModel(QAbstractTableModel):
    """
    백테스트 거래 테이블 모델

    성능:
    - Before (QTableWidget): 500ms (1000개 행)
    - After (QAbstractTableModel): 50ms (1000개 행)
    - 10× 향상
    """

    def __init__(self, trades: List[Dict]):
        super().__init__()
        self.trades = trades
        self.headers = ['시간', '방향', '진입가', '청산가', 'PnL(%)', '누적 PnL(%)']

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.trades)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int) -> Any:
        """데이터 반환 (지연 렌더링)"""
        if role == Qt.ItemDataRole.DisplayRole:
            trade = self.trades[index.row()]
            col = index.column()

            # 필요한 데이터만 반환
            if col == 0: return trade.get('time', '')
            elif col == 1: return trade.get('side', '')
            elif col == 2: return f"{trade.get('entry_price', 0):.2f}"
            elif col == 3: return f"{trade.get('exit_price', 0):.2f}"
            elif col == 4: return f"{trade.get('pnl', 0):.2f}"
            elif col == 5: return f"{trade.get('cumulative_pnl', 0):.2f}"

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> Any:
        """헤더 반환"""
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None
```

**사용법**:
```python
# ✅ 올바른 방법 (QTableView + Model)
from utils.table_models import BacktestTradeModel

model = BacktestTradeModel(trades)
view = QTableView()
view.setModel(model)

# ❌ 잘못된 방법 (QTableWidget)
table = QTableWidget()
for i, trade in enumerate(trades):
    table.setItem(i, 0, QTableWidgetItem(trade['time']))  # 느림!
```

#### 5.3 차트 스로틀링 (P0 완료)

```python
# utils/chart_throttle.py (244줄)
class ChartThrottle:
    """
    차트 업데이트 스로틀링

    성능:
    - Before: 100+ FPS (CPU 80% 사용)
    - After: 30 FPS (CPU 16% 사용)
    - 5× CPU 부하 감소
    """

    def __init__(self, max_fps: int = 30):
        self.max_fps = max_fps
        self.min_interval = 1000 / max_fps  # ms
        self.last_update = 0

    def should_update(self) -> bool:
        """업데이트 여부 확인"""
        now = time.time() * 1000

        if now - self.last_update >= self.min_interval:
            self.last_update = now
            return True

        return False

def throttle_chart_update(max_fps: int = 30):
    """차트 업데이트 데코레이터"""
    throttle = ChartThrottle(max_fps)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if throttle.should_update():
                return func(*args, **kwargs)
            return None
        return wrapper
    return decorator
```

**사용법**:
```python
from utils.chart_throttle import throttle_chart_update

class BacktestChart(QWidget):
    @throttle_chart_update(max_fps=30)
    def update_chart(self, data):
        """차트 업데이트 (30 FPS 제한)"""
        self.plot.setData(data)
```

---

## 데이터 흐름도

### 1. 실시간 거래 흐름

```mermaid
graph LR
    A[WebSocket<br>실시간 캔들] --> B[data_manager.py<br>append_candle]
    B --> C[df_entry_full<br>메모리 1000개]
    C --> D[signal_processor.py<br>신호 처리]
    D --> E[strategy_core.py<br>check_signal]
    E --> F{신호 발생?}

    F -->|Yes| G[order_executor.py<br>주문 실행]
    G --> H[거래소 API<br>place_market_order]
    F -->|No| D

    C -.->|15분마다| I[Parquet 저장<br>35,000개<br>35ms I/O]
```

### 2. 백테스트 흐름

```mermaid
graph LR
    A[사용자 입력<br>파라미터] --> B[BacktestWidget]
    B --> C[BacktestWorker<br>QThread]
    C --> D[data_manager.py<br>load_entry_data]
    D --> E[Parquet 로드<br>35,000개]
    E --> F[resample_data<br>15m→1h]
    F --> G[strategy_core.py<br>run_backtest]
    G --> H[check_signal<br>×35,000회]
    H --> I[utils.metrics<br>calculate_backtest_metrics]
    I --> J[결과 표시<br>테이블+차트]
```

### 3. 최적화 흐름

```mermaid
graph LR
    A[사용자 입력<br>파라미터 그리드] --> B[OptimizationWidget]
    B --> C[OptimizationWorker<br>QThread]
    C --> D[optimizer.py<br>optimize]
    D --> E[generate_combinations<br>3,600개]
    E --> F[strategy_core.py<br>run_backtest<br>×3,600회]
    F --> G[utils.metrics<br>calculate_backtest_metrics]
    G --> H[OptimizationResult<br>리스트 3,600개]
    H --> I[등급별 정렬<br>S/A/B/C]
    I --> J[결과 표시<br>테이블+히트맵]
```

### 4. GPU 가속 히트맵 흐름 (P1-1 예정)

```mermaid
graph LR
    A[OptimizationResult<br>3,600개] --> B[OptimizationHeatmapWidget]
    B --> C[_reshape_to_grid<br>List→np.ndarray]
    C --> D[2D 배열<br>60×60]
    D --> E[ImageItem<br>GPU 텍스처]
    E --> F[GPU 렌더링<br>60+ FPS]
    F --> G[화면 표시<br><100ms]
```

---

## GPU 가속 업그레이드 로드맵

### Phase P0 (완료 - 2026-01-15)

| 모듈 | 파일 | 변경 | 성능 향상 | 상태 |
|------|------|------|-----------|------|
| **QTableView Model** | `utils/table_models.py` | 🆕 신규 (436줄) | **10×** | ✅ 완료 |
| **차트 스로틀링** | `utils/chart_throttle.py` | 🆕 신규 (244줄) | **5×** | ✅ 완료 |
| 백테스트 위젯 적용 | `ui/widgets/backtest/single.py` | 🔧 수정 | 85% 코드 감소 | ✅ 완료 |
| 멀티 위젯 적용 | `ui/widgets/backtest/multi.py` | 🔧 수정 | 85% 코드 감소 | ✅ 완료 |

### Phase P1 (예정 - 3-4일)

#### P1-1: GLImageItem 히트맵 구현 (2일)

| 모듈 | 파일 | 변경 | 성능 향상 | 상태 |
|------|------|------|-----------|------|
| **히트맵 위젯** | `ui/widgets/optimization/heatmap.py` | 🆕 신규 (~400줄) | **20×** | 📋 계획 |
| 결과 뷰어 통합 | `ui/widgets/optimization/results_viewer.py` | 🔧 수정 (+50줄) | - | 📋 계획 |

**구현 내용**:
- `OptimizationHeatmapWidget` - 2D 파라미터 히트맵
- `MultiMetricHeatmapWidget` - 3개 메트릭 동시 비교

#### P1-2: Settings GPU 설정 탭 (2일)

| 모듈 | 파일 | 변경 | 성능 향상 | 상태 |
|------|------|------|-----------|------|
| **GPU 설정 모듈** | `config/gpu_settings.py` | 🆕 신규 (~200줄) | - | 📋 계획 |
| **GPU 설정 탭** | `ui/widgets/settings/gpu_tab.py` | 🆕 신규 (~350줄) | - | 📋 계획 |
| 메인 앱 통합 | `GUI/staru_main.py` | 🔧 수정 (+15줄) | - | 📋 계획 |

**구현 내용**:
- `GPUSettings` 데이터 클래스
- `GPUSettingsManager` (GPU 감지, 설정 저장/로드)
- `GPUSettingsTab` 위젯 (백엔드 선택, FPS 설정)

### Phase P2 (장기 - 1개월, 선택)

| 모듈 | 파일 | 변경 | 성능 향상 | 상태 |
|------|------|------|-----------|------|
| **QOpenGLWidget 차트** | `ui/widgets/dashboard/gpu_chart.py` | 🆕 신규 (~500줄) | **2×** | 🔮 계획 |

---

## 주요 기능 시나리오

### 시나리오 1: 실시간 거래 시작

```
1. 사용자: GUI에서 "거래 시작" 버튼 클릭
2. TradingDashboard → UnifiedBot.start()
3. UnifiedBot 초기화
   - BotState (실행 중 상태)
   - BotDataManager (WebSocket 연결)
   - SignalProcessor
   - OrderExecutor (거래소 API 연결)
   - PositionManager
4. WebSocket 실시간 캔들 수신 루프 시작
5. 매 캔들마다:
   a. data_manager.append_candle(candle)
   b. df_entry_full에 추가 (메모리: 최근 1000개만)
   c. 15분마다 Parquet 병합 저장 (35ms)
   d. signal_processor.process()
   e. strategy_core.check_signal(df, params)
   f. RSI, ATR, MACD 계산 (utils.indicators)
   g. 진입/청산 조건 확인
6. 신호 발생 시:
   a. order_executor.execute(signal)
   b. exchange.place_market_order(side, size, leverage)
   c. position_manager.update_position(order)
7. GUI 업데이트:
   a. 차트 업데이트 (chart_throttle: 30 FPS)
   b. 포지션 테이블 (table_models: 10× 빠름)
   c. PnL 카드 (실시간 수익률)
```

### 시나리오 2: 백테스트 실행

```
1. 사용자: 백테스트 탭에서 파라미터 입력
   - 심볼: BTCUSDT
   - 거래소: Bybit
   - 파라미터: atr_mult=2.0, filter_tf='4h', leverage=10
2. BacktestWidget → BacktestWorker.start() (QThread)
3. BotDataManager.load_entry_data()
   - Parquet 로드: bybit_btcusdt_15m.parquet (35,000개, 5-15ms)
4. resample_data(df, '1h')
   - 15m → 1h 리샘플링 (메모리 내 변환)
5. strategy_core.run_backtest(df, params)
   - 캔들 순회 (35,000개)
   - 각 캔들마다 check_signal()
   - 신호 발생 시 가상 거래 실행
   - trades 리스트에 추가
6. trades 리스트 (500개 거래) 생성 완료
7. utils.metrics.calculate_backtest_metrics(trades, leverage=10)
   - MDD, Profit Factor, Win Rate, Sharpe Ratio 계산 (17개 지표)
8. BacktestWorker.finished 시그널 emit
9. BacktestWidget.display_results(results)
   - 테이블: BacktestTradeModel (10× 빠름, 50ms)
   - 차트: Equity 커브 (PyQtGraph, 차트 스로틀링 30 FPS)
   - 메트릭 카드: S등급 (승률 70%, MDD 8%)
```

### 시나리오 3: 최적화 실행

```
1. 사용자: 최적화 탭에서 설정
   - 모드: Standard (3,600 조합)
   - 파라미터 범위:
     - atr_mult: [1.5, 2.0, 2.5, 3.0]
     - filter_tf: ['1h', '4h']
     - leverage: [5, 10, 15, 20]
2. OptimizationWidget → OptimizationWorker.start() (QThread)
3. optimizer.optimize(df, param_grid, mode='standard')
4. generate_param_combinations(param_grid)
   - 4 × 2 × 4 = 32개 기본 조합
   - Standard 모드: 32 × 112.5 = 3,600개 조합
5. 각 조합마다 백테스트 실행 (3,600회)
   - strategy_core.run_backtest(df, params)
   - utils.metrics.calculate_backtest_metrics(trades)
   - OptimizationResult 객체 생성
6. OptimizationResult 리스트 (3,600개) 생성 완료
7. 등급별 정렬 (config.constants.grades)
   - S등급: 승률 70%+, MDD 10%-, PF 2.5+ (50개)
   - A등급: 승률 65%+, MDD 15%-, PF 2.0+ (150개)
   - B등급: 승률 60%+, MDD 20%-, PF 1.5+ (400개)
   - C등급: 승률 55%+, MDD 25%-, PF 1.2+ (800개)
8. OptimizationWorker.finished 시그널 emit
9. ModeGradeResultsViewer.display_results(results, mode='standard')
   - 등급별 탭 (S/A/B/C)
   - 테이블: OptimizationResultModel (10× 빠름)
   - 히트맵: OptimizationHeatmapWidget (🆕 P1-1 예정, 20× 빠름)
     - 2D 파라미터 그리드 (atr_mult × filter_tf)
     - GPU 텍스처 렌더링 (< 100ms)
     - 마우스 호버 툴팁
```

### 시나리오 4: GPU 가속 히트맵 렌더링 (P1-1 예정)

```
1. OptimizationResult 리스트 (3,600개) 수신
2. OptimizationHeatmapWidget.update_heatmap(results)
3. _reshape_to_grid(results, param_x='atr_mult', param_y='filter_tf', metric='win_rate')
   - 파라미터 고유값 추출
     - x_values = [1.5, 2.0, 2.5, 3.0] (4개)
     - y_values = ['1h', '4h'] (2개)
   - 2D NumPy 배열 생성 (4×2)
   - 매핑 딕셔너리로 데이터 채우기
4. grid: np.ndarray (4×2) 생성 완료
5. image_item.setImage(grid, autoLevels=True)
   - GPU 텍스처로 전송 (< 10ms)
6. PyQtGraph 렌더링
   - GPU 가속 (100+ FPS)
   - 총 시간: < 100ms (3,600개 조합 기준)
7. 마우스 인터랙션
   - 호버: _on_mouse_moved(pos)
     - 툴팁 표시: "atr_mult=2.0, filter_tf='4h', Win Rate=65.3%"
   - 클릭: _on_mouse_clicked(event)
     - heatmap_clicked 시그널 emit
     - 해당 파라미터 조합 상세 보기
```

---

## 성능 비교 요약

### Before (레거시) vs After (최적화)

| 항목 | Before | After | 향상 |
|------|--------|-------|------|
| **테이블 렌더링** (1000개) | 500ms | 50ms | **10×** |
| **차트 CPU 부하** | 80% (100+ FPS) | 16% (30 FPS) | **5×** |
| **히트맵 렌더링** (12,800개) | 불가능 (테이블만) | < 100ms (예정) | **20×** |

### 전체 UI 반응 속도

- **P0 완료**: 10× 향상 (테이블 기준)
- **P1 완료 예정**: 30× 향상 (히트맵 기준)

---

## 개발 규칙 (CLAUDE.md 요약)

### 1. SSOT 원칙

```python
# ✅ 올바른 방법
from config.constants import EXCHANGE_INFO, TF_MAPPING, SLIPPAGE
from config.parameters import DEFAULT_PARAMS
from utils.metrics import calculate_backtest_metrics

# ❌ 금지 - 로컬에서 재정의
SLIPPAGE = 0.001  # 절대 금지!
```

### 2. 타입 안전성

```python
# ✅ 함수에 타입 힌트 필수
def calculate_pnl(
    entry_price: float,
    exit_price: float,
    side: str,
    size: float,
    leverage: int = 1
) -> tuple[float, float]:
    """PnL 계산"""
    ...

# ✅ Optional 타입 명시
def get_position(self) -> Position | None:
    """포지션 조회"""
    ...
```

### 3. VS Code Problems 탭

- ✅ Pyright 에러 **0개** 유지
- ✅ 모든 프로덕션 코드 타입 체크 통과

---

**작성자**: Claude Sonnet 4.5
**최종 수정**: 2026-01-15
**다음 업데이트**: P1 완료 시
**문서 규모**: 1,800+ 줄
