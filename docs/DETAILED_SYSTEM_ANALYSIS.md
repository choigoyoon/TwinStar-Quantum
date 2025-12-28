# TwinStar Quantum: 상세 시스템 아키텍처 및 코드 분석 보고서

본 보고서는 **TwinStar Quantum** 트레이딩 플랫폼의 전체 코드 베이스를 심층 분석하여, 모듈 간의 유기적인 결합 구조, 임포트 목적, 데이터 흐름, 그리고 EXE 배포를 위한 기술적 장치들을 상술합니다.

---

## 1. 종합 시스템 아키텍처 다이어그램 (Extensive Mermaid)

본 시스템은 엄격한 계층화 아키텍처(Layered Architecture)를 따르며, 중심부의 전략 엔진(Brain)과 외부 통신(Bridge)이 철저히 분리되어 있습니다.

```mermaid
graph TD
    %% [Entry Point]
    Main["<b>GUI/staru_main.py</b><br/>(System Orchestrator)"]

    %% [Security & License]
    Main --> LM["<b>license_manager.py</b><br/>(Server Auth/Tiering)"]
    Main --> Login["GUI/login_dialog.py"]
    LM -.-> AES["GUI/crypto_manager.py"]

    %% [UI Layer - High Level Widgets]
    subgraph UI_Layer [Frontend Layer (PyQt5)]
        Main --> Dash["<b>trading_dashboard.py</b><br/>(Real-time Monitor)"]
        Main --> Backtest["<b>backtest_widget.py</b><br/>(Strategy Simulation)"]
        Main --> Opt["<b>optimization_widget.py</b><br/>(Param Finder)"]
        Main --> DataCol["data_collector_widget.py"]
        
        %% UI Support
        Dash --> BotStatus["GUI/bot_status_widget.py"]
        Dash --> Const["GUI/constants.py"]
        Main --> Theme["GUI/styles.py"]
    end

    %% [Logic Layer - The Engine]
    subgraph Engine_Layer [Core Logic Engine]
        Dash --> UnifiedBot["<b>unified_bot.py</b><br/>(Execution Engine)"]
        Backtest --> UnifiedBot
        Opt --> Optimizer["<b>optimizer.py</b><br/>(Parallel Engine)"]
        
        UnifiedBot --> Strategy["<b>strategy_core.py</b><br/>(Signal/Math Logic)"]
        Optimizer --> Strategy
        
        %% Sub-components
        UnifiedBot --> Presets["preset_manager.py"]
        Strategy --> SMC["smc_utils.py"]
    end

    %% [Infrastructure Layer]
    subgraph Infra_Layer [Data & Communication]
        UnifiedBot --> ExMgr["<b>exchange_manager.py</b><br/>(Unified Bridge)"]
        ExMgr --> Binance["exchanges/binance_exchange.py"]
        ExMgr --> Bybit["exchanges/bybit_exchange.py"]
        ExMgr --> Korea["exchanges/upbit_bithumb.py"]
        ExMgr --> WS["exchanges/ws_handler.py"]

        %% Persistent Storage
        UnifiedBot --> TradeStore["trade_storage.py"]
        UnifiedBot --> StateStore["state_storage.py"]
        Dash --> SecureStore["secure_storage.py"]
    end

    %% [The Foundation]
    subgraph Foundation [System Foundation]
        All_Modules --> Paths["<b>paths.py</b><br/>(EXE Path Glue)"]
        Main --> Health["system_doctor.py"]
        Main --> ErrorG["error_guide.py"]
    end

    %% Data Flow
    Binance -- "Real-time Stream" --> WS
    WS -- "Ticks/Klines" --> UnifiedBot
    Strategy -- "Signal (W/M)" --> UnifiedBot
    UnifiedBot -- "Orders" --> ExMgr
```

---

## 2. 모듈별 심층 분석 및 임포트 상황 (Purpose of Imports)

### 2.1. 컨트롤 타워: `GUI/staru_main.py`
*   **용도**: 전체 어플리케이션의 생명주기를 관리합니다.
*   **주요 임포트 상황**:
    *   `PyQt5`: GUI 렌더링 및 이벤트 루프.
    *   `paths.py`: 프로그램 시작 즉시 파일 시스템 경로를 초기화합니다.
    *   `license_manager`: 미인증 사용자의 접근을 차단합니다.
    *   `system_doctor`: 부팅 시 누락된 폴더나 깨진 설정 파일을 자동 복구합니다.
    *   **Lazy Loading**: 초기 로딩 속도 향상을 위해 각 위젯 탭을 `load_widget` 함수로 지연 로딩합니다.

### 2.2. 실행 엔진: `unified_bot.py`
*   **용도**: 백테스트와 실매매 로직이 100% 동일하게 작동하도록 설계된 통합 엔진입니다.
*   **주요 임포트 상황**:
    *   `strategy_core.py`: 신호 감지 및 포지션 관리 로직을 위임받습니다.
    *   `exchange_manager.py`: 실제 주문을 넣을 하이레벨 어댑터를 가져옵니다.
    *   `trade_storage`: 모든 체결 내역을 SQLite/CSV로 영구 기록합니다.
    *   `time (Monkey Patch)`: 거래소 서버와의 시간 오프셋을 보정하여 `API 10002 (Request Expired)` 에러를 원천 전 차단합니다.

### 2.3. 전략 본체: `strategy_core.py`
*   **용도**: Alpha-X7 전략의 수학적 모델링입니다. 외부 의존성(거래소, UI) 없이 순수 데이터로만 작동합니다.
*   **핵심 로직**:
    *   **MACD Divergence**: W/M 패턴의 신뢰도를 결정합니다.
    *   **Adaptive ATR**: 시장 변동성에 따라 익절/손절 범위를 가변적으로 조정합니다.
    *   **MTF Filter**: 4시간(4H) 추세가 아닐 경우 15분(15m) 진입 신호를 무시하여 승률을 높입니다.

### 2.4. 인프라 기반: `paths.py`
*   **용도**: "개발용 Py"와 "배포용 EXE"의 차이를 메우는 접착제입니다.
*   **임포트 목적**: 모든 파일 관련 모듈(`os`, `shutil`, `pathlib`)보다 먼저 참조되어 `BASE_DIR`과 `INTERNAL_BASE`를 확정 짓습니다.

---

## 3. 핵심 데이터 흐름 (Data Flow)

1.  **시세 유입**: `exchange_manager` $\rightarrow$ `ws_handler` $\rightarrow$ `unified_bot` (Pandas DataFrame으로 축적)
2.  **분석**: `unified_bot`이 `strategy_core.detect_signal()` 호출 $\rightarrow$ W/M 패턴 감지.
3.  **의사결정**: MTF 추세 확인 $\rightarrow$ 적응형 파라미터 계산 $\rightarrow$ 진입 결정.
4.  **주문**: `unified_bot` $\rightarrow$ `exchange_manager` $\rightarrow$ 특정 거래소 어댑터 (`binance_exchange` 등) $\rightarrow$ 시장가/지정가 주문.
5.  **사후관리**: `strategy_core.manage_position_realtime()`을 통해 자산 1초 단위 추적 및 Trailing Stop 적용.

---

## 4. 보안 및 스토리지 아키텍처

| 모듈명 | 저장 대상 | 보안 방식 |
| :--- | :--- | :--- |
| **`secure_storage.py`** | API Key, Secret | Fernet Symmetric Encryption (AES-128 기반) |
| **`license_manager.py`** | 기기 고유 ID (HWID) | 서버 사이드 해싱 및 RSA 서명 검증 |
| **`state_storage.py`** | 봇 현재 잔고, 포지션 | JSON Serialization + 주기적 자동 백업 |
| **`trade_history.py`** | 과거 모든 거래 기록 | SQLite 3 (대용량 쿼리 최적화) |

---

## 5. EXE 패킹을 위한 특수 설계

본 프로젝트는 PyInstaller 빌드 시 발생할 수 있는 "경로 누락"을 방지하기 위해 다음 장치들을 갖추고 있습니다.

*   **`_MEIPASS` 감지**: `paths.py`와 `staru_main.py`에서 `sys.frozen` 여부를 검사하여 내부 리소스(Assets, QSS) 경로를 동적으로 변경합니다.
*   **자동 캐시 비우기**: 개발 환경 실행 시 `__pycache__`를 자동 삭제하여, 빌드 시 오염된 바이트코드가 포함되지 않도록 관리합니다.
*   **Separated Data Dir**: EXE 실행 파일과 데이터 저장 폴더(`user`, `data`, `logs`)를 명확히 분리하여 윈도우 권한 문제(ReadOnly)를 우회합니다.

---
*작성일: 2025-12-18*  
*문서 버전: v2.5 (Detailed Analysis)*  
*작성 도구: TwinStar Quantum AI Architect (DeepMind)*
