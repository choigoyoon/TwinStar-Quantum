# 샌드박스 최적화 모듈 v1.2.0

W/M 패턴 탐지 기반 자동매매 백테스트 및 최적화 모듈

## 📋 개요

두 가지 독립적인 패턴 탐지 전략을 제공:

| 전략 | 원리 | 특징 |
|------|------|------|
| **MACD** | MACD 히스토그램 부호 전환 | 높은 승률, 안정적 |
| **ADX/DI** | +DI/-DI 크로스오버 | 많은 거래, 트렌드 민감 |

## 📁 모듈 구조

```
sandbox_optimization/
├── __init__.py          # 패키지 API (v1.2.0)
├── constants.py         # 비용 상수, 기본값
├── presets.py           # 파라미터 프리셋 (7개)
├── filters.py           # 진입 필터 (Stochastic, Downtrend)
├── base.py              # 공통 로직 (지표, 백테스트 코어)
├── interface.py         # UI 연결용 인터페이스 ⭐
├── core.py              # 레거시 호환 (deprecated)
├── strategies/
│   ├── __init__.py
│   ├── macd.py          # MACD 전략 (독립 모듈)
│   └── adxdi.py         # ADX/DI 전략 (독립 모듈)
├── presets/
│   └── bybit_btcusdt_1h.json
├── OPTIMIZATION_REPORT.md
└── README.md
```

## 🚀 빠른 시작

### 방법 1: 전략 클래스 직접 사용 (권장)

```python
from sandbox_optimization.strategies import MACDStrategy, ADXDIStrategy
from sandbox_optimization import SANDBOX_PARAMS
import pandas as pd

# 데이터 로드
df = pd.read_parquet('parquet/bybit_btcusdt_15m.parquet')

# MACD 전략
macd = MACDStrategy(SANDBOX_PARAMS)
result = macd.backtest(df, timeframe='1h', apply_filters=True)
print(f"MACD: {result['trades']}건, 승률 {result['win_rate']:.1f}%")

# ADX/DI 전략
adxdi = ADXDIStrategy(SANDBOX_PARAMS)
result = adxdi.backtest(df, timeframe='1h', apply_filters=True)
print(f"ADX/DI: {result['trades']}건, 승률 {result['win_rate']:.1f}%")
```

### 방법 2: UI 인터페이스 사용 (PyQt/Streamlit용)

```python
from sandbox_optimization.interface import (
    run_strategy, 
    compare_strategies, 
    get_available_options,
    StrategyRunner
)

# 단일 전략 실행
result = run_strategy(df, strategy='macd', timeframe='1h')

# 두 전략 비교
comparison = compare_strategies(df, timeframe='1h')
print(f"승자: {comparison['comparison']['winner']}")

# 클래스 기반 (UI에서 상태 유지)
runner = StrategyRunner()
runner.load_data('parquet/bybit_btcusdt_15m.parquet')
result = runner.run('macd', '1h')
print(runner.get_summary())
```

### 방법 3: 레거시 방식 (기존 코드 호환)

```python
from sandbox_optimization import run_backtest, run_optimization, SANDBOX_PARAMS

# 백테스트
result = run_backtest(df, SANDBOX_PARAMS, timeframe='1h', method='macd')

# 최적화
results = run_optimization(df, timeframe='1h', method='macd', mode='quick')
```

## 📊 성능 비교 (1h TF, 2020~)

| 전략 | 거래 수 | 승률 | PnL | MDD |
|------|---------|------|-----|-----|
| MACD | 2,216 | 83.8% | +2,077% | 10.9% |
| ADX/DI | 2,572 | 78.8% | +1,938% | 11.1% |

## 🔧 파라미터 설명

### 기본 파라미터 (SANDBOX_PARAMS)

```python
{
    'atr_mult': 1.5,         # ATR 배수 (손절 거리)
    'trail_start': 1.2,      # 트레일링 시작점 (리스크 배수)
    'trail_dist': 0.03,      # 트레일링 거리 (리스크 배수)
    'tolerance': 0.10,       # W/M 패턴 허용 오차
    'adx_min': 10,           # 최소 ADX 값
    'stoch_long_max': 50,    # Long 진입 Stoch 상한
    'stoch_short_min': 50,   # Short 진입 Stoch 하한
    'use_downtrend_filter': True,  # 다운트렌드 필터 사용
}
```

### 프리셋 목록

| 프리셋 | 특징 | 용도 |
|--------|------|------|
| `SANDBOX_PARAMS` | 기본값 | 범용 |
| `FILTER_ATR_OPTIMAL` | ATR 2.5 | 수익 극대화 |
| `BALANCED_OPTIMAL` | ATR 2.0 | 밸런스 |
| `STABLE_OPTIMAL` | 보수적 | 안정형 |

## 🎯 필터 시스템

### Stochastic 필터
- **Long 진입**: `stoch_k ≤ 50` (과매도 영역)
- **Short 진입**: `stoch_k ≥ 50` (과매수 영역)

### Downtrend 필터
- **Short 진입**: `EMA21 < EMA50` (하락 추세에서만)

### 필터 효과

| 설정 | 거래 수 | 승률 | PnL |
|------|---------|------|-----|
| 필터 ON | 2,216 | 83.8% | +2,077% |
| 필터 OFF | 3,735 | 79.9% | +2,961% |

## 📝 UI 연결 가이드

### PyQt 예시

```python
from sandbox_optimization.interface import StrategyRunner, get_available_options

class TradingWidget(QWidget):
    def __init__(self):
        self.runner = StrategyRunner()
        
        # 옵션 로드
        options = get_available_options()
        self.strategy_combo.addItems(options['strategies'])
        self.timeframe_combo.addItems(options['timeframes'])
    
    def on_run_clicked(self):
        result = self.runner.run(
            strategy=self.strategy_combo.currentText(),
            timeframe=self.timeframe_combo.currentText(),
        )
        self.result_label.setText(self.runner.get_summary())
```

### Streamlit 예시

```python
import streamlit as st
from sandbox_optimization.interface import run_strategy, get_available_options

options = get_available_options()

strategy = st.selectbox("전략", options['strategies'])
timeframe = st.selectbox("타임프레임", options['timeframes'])

if st.button("실행"):
    result = run_strategy(df, strategy=strategy, timeframe=timeframe)
    st.metric("승률", f"{result['win_rate']:.1f}%")
    st.metric("PnL", f"{result['simple_pnl']:+.1f}%")
```

## 💰 비용 계산

```
편도 슬리피지: 0.06%
편도 수수료:   0.055% (Bybit Taker)
─────────────────────
편도 합계:     0.115%
왕복 합계:     0.23%
```

## 📄 라이선스

MIT License
