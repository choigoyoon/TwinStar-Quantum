# TwinStar Quantum v1.7.0 구조

## 폴더 구조
C:\매매전략\
├── core/
│   ├── unified_bot.py (360줄) - 메인 봇 (Websocket + 모듈 조율)
│   ├── bot_state.py - 상태 관리 (저장/로드, Atomic Write)
│   ├── data_manager.py - 데이터 관리 (캔들, 지표 계산)
│   ├── signal_processor.py - 시그널 처리 (패턴 감지, 필터링)
│   ├── order_executor.py - 주문 실행 (진입, 청산, SL 설정)
│   ├── position_manager.py - 포지션 관리 (Trailing SL, 상태 동기화)
│   └── strategy_core.py - 전략 엔진 (Alpha-X7 파라미터 로직)
├── config/
│   ├── parameters.py - 파라미터 SSOT (Single Source of Truth)
│   └── presets/ - 프리셋 JSON 파일
├── utils/
│   ├── indicators.py - 지표 계산 SSOT (RSI, ATR, MACD, EMA)
│   └── preset_manager.py - 프리셋 로드/관리
├── exchanges/
│   ├── base_exchange.py - 거래소 추상 클래스
│   ├── bybit_exchange.py - Bybit 구현
│   ├── binance_exchange.py - Binance 구현
│   ├── okx_exchange.py - OKX 구현
│   ├── bitget_exchange.py - Bitget 구현
│   └── bithumb_exchange.py - Bithumb 구현
├── GUI/
│   ├── trading_dashboard.py - 메인 대시보드
│   ├── optimization_widget.py - 최적화 UI
│   └── staru_main.py - 진입점
└── backups/ - 백업 파일 보관소

## Import 규칙

### 1. 파라미터 (SSOT)
모든 전략 파라미터는 `config.parameters`에서만 가져옵니다.
```python
from config.parameters import DEFAULT_PARAMS, get_param
# 사용 예: get_param('atr_mult')
```

### 2. 지표 계산 (SSOT)
모든 기술적 지표 계산은 `utils.indicators`를 사용합니다.
```python
from utils.indicators import calculate_rsi, calculate_atr
```

### 3. 모듈 내부 참조
`core` 패키지 내부에서는 상대 경로(`from .xxx import yyy`)를 권장하지 않으며, **절대 경로**(`from core.xxx import yyy`)나 명시적 임포트를 선호합니다. (EXE 빌드 호환성)

## 모듈 역할 (Delegation)

| 모듈 | 역할 | 주요 메서드 |
|------|------|------------|
| **unified_bot.py** | 오케스트레이션 | `run()`, `detect_signal()`, `_init_modular_components()` |
| **bot_state.py** | 영속성 관리 | `save_state()`, `load_state()`, `save_trade()` |
| **data_manager.py** | 데이터 처리 | `load_historical()`, `process_all()`, `backfill()` |
| **signal_processor.py** | 시그널 생성 | `filter_valid_signals()`, `get_trading_conditions()` |
| **order_executor.py** | 실행/검증 | `execute_entry()`, `execute_close()`, `set_leverage()` |
| **position_manager.py** | 포지션 추적 | `manage_live()`, `check_sl_hit()`, `sync_with_exchange()` |

## 버전 정보
- **Version**: v1.7.0
- **Release Date**: 2026-01-01
- **Key Features**: Modular Architecture, Parameter Centralization, Atomic State Save, Enhanced Reliability
