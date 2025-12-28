# TwinStar Quantum 시스템 아키텍처 및 임포트 다이어그램

본 보고서는 **TwinStar Quantum** 프로젝트의 핵심 모듈 간의 의존성 구조와 EXE 패킹을 위한 경로 관리 체계를 설명합니다.

---

## 1. 시스템 아키텍처 다이어그램 (Mermaid)

현재 프로젝트의 주요 모듈 간 임포트 관계를 시각화한 다이어그램입니다.

```mermaid
graph TD
    %% Entry Point
    Main[GUI/staru_main.py] -- "1. 인증 및 앱 시작" ---o App

    %% UI Layer
    subgraph UI_Layer [GUI Widgets]
        Main --> Dashboard[GUI/trading_dashboard.py]
        Main --> BacktestUI[GUI/backtest_widget.py]
        Main --> OptUI[GUI/optimization_widget.py]
        Main --> SettingsUI[GUI/settings_widget.py]
    end

    %% Logic Layer
    subgraph Logic_Layer [Core Trading Logic]
        Dashboard --> Bot[unified_bot.py]
        BacktestUI --> Bot
        OptUI --> Optimizer[optimizer.py]
        Bot --> Strategy[strategy_core.py]
        Optimizer --> Strategy
    end

    %% Infrastructure Layer
    subgraph Infrastructure [Data & Systems]
        Bot --> ExMgr[exchange_manager.py]
        ExMgr --> Adapters[exchanges/*.py]
        
        Bot --> Storage[trade_storage.py / state_storage.py]
        Main --> LM[license_manager.py]
        
        %% Utils
        Logic_Layer --> Paths[paths.py]
        Infrastructure --> Paths
        Logic_Layer --> Constants[GUI/constants.py]
    end

    %% Styling
    classDef entry fill:#f96,stroke:#333,stroke-width:4px;
    classDef logic fill:#bbf,stroke:#333;
    classDef storage fill:#dfd,stroke:#333;
    class Main entry;
    class Bot,Strategy logic;
    class Storage,ExMgr storage;
```

---

## 2. 계층별 상세 역할

### 🏛️ Entry & Management (최상위)
*   **`GUI/staru_main.py`**: 어플리케이션의 진입점입니다. `license_manager`를 통한 보안 인증을 수행하며, 모든 UI 위젯을 관리합니다.
*   **`license_manager.py`**: 서버 기반의 라이선스 검증 및 사용자 티어(Admin/User) 관리를 담당합니다.

### 🖼️ UI Layer (사용자 인터페이스)
*   **`trading_dashboard.py`**: 실시간 시장 데이터 시각화 및 봇 실행/중지를 제어하는 핵심 대시보드입니다.
*   **`backtest_widget.py`**: 과거 Parquet 데이터를 기반으로 전략의 수익률을 시뮬레이션하는 인터페이스입니다.
*   **`optimization_widget.py`**: 수천 개의 파라미터 조합을 테스트하여 최적의 설정값을 찾는 UI입니다.

### 🧠 Core Logic (매매 및 전략)
*   **`unified_bot.py`**: 실제 매매 루프를 실행하는 엔진입니다. 백테스트와 실매매 로직이 통합되어 있어 환경 간의 괴리를 최소화합니다.
*   **`strategy_core.py`**: **Alpha-X7 전략**의 본체입니다. 패턴 감지(W/M), 추세 필터링, RSI 기반 적응형 트레일링 스탑 로직을 포함합니다.
*   **`optimizer.py`**: 대량의 데이터에 대해 전략 로직을 병렬로 수행하여 최적의 수익 곡선을 산출합니다.

### 💾 Infrastructure (데이터 및 통신)
*   **`exchange_manager.py`**: CCXT 기반의 글로벌 거래소와 한국 전용 어댑터(Upbit/Bithumb)를 통합 관리하는 게이트웨이입니다.
*   **`exchanges/`**: 각 거래소별 API 특화 로직(WebSocket 핸들링, 주문 규격 등)이 표준화되어 있습니다.
*   **`paths.py`**: 프로젝트의 심장과 같은 역할입니다. 개발 환경(Python)과 배포 환경(EXE) 간의 경로 차이( `_MEIPASS` 등)를 추상화하여 모든 모듈이 안전하게 파일에 접근하도록 돕습니다.

---

## 3. EXE 패킹 핵심 사항 (Path Management)

TwinStar Quantum은 PyInstaller를 통한 단일 실행 파일 배포를 위해 다음의 경로 규칙을 엄격히 준수합니다.

1.  **가상 내부 경로 (`INTERNAL_BASE`)**: EXE 내부에 포함된 리소스(`assets`, `styles.qss`, `presets`)에 접근할 때 사용됩니다.
2.  **외부 영구 경로 (`BASE`)**: 실제 실행 파일이 위치한 폴더입니다. 사용자 설정(`user/`), 로그(`logs/`), 캐시 데이터(`data/`) 등이 저장되는 '쓰기 가능' 영역입니다.
3.  **코드 모듈**: 모든 `.py` 모듈은 `staru_clean.spec` 설정에 의해 EXE 내부 패키지로 포함되며, 실행 시 `sys.path`에 로드됩니다.

---
*작성일: 2025-12-18*  
*작성자: TwinStar Quantum 개발팀*
