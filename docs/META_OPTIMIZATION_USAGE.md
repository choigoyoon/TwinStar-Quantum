# Meta 최적화 사용법

## 1. Meta 최적화 실행 (자동 범위 탐색)

```bash
python -c "
from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core
from core.meta_optimizer import MetaOptimizer
from utils.indicators import add_all_indicators

# 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
dm.load_historical()
df = dm.df_entry_full.copy().set_index('timestamp')
df = df.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna().reset_index()
df = add_all_indicators(df, inplace=False)

# Meta 최적화
optimizer = BacktestOptimizer(AlphaX7Core, df, 'macd')
meta = MetaOptimizer(optimizer, sample_size=200, max_iterations=3)
result = meta.run_meta_optimization(df, trend_tf='1h', metric='sharpe_ratio')

# 결과 저장
meta.save_meta_ranges('bybit', 'BTCUSDT', '1h')
"
```

**결과**: `presets/meta_ranges/bybit_BTCUSDT_1h_meta_YYYYMMDD.json`

---

## 2. Meta 결과로 백테스트

### 방법 1: 초간단 (1개 조합)

```bash
python tools/test_meta_result.py
```

### 방법 2: 비교 (3개 조합)

```bash
python tools/compare_meta_params.py
```

---

## 3. 결과 해석

### Meta 최적화 결과 (Bybit BTC/USDT 1h)

```json
{
  "iterations": 2,
  "convergence_reason": "improvement_below_threshold",
  "param_ranges_by_mode": {
    "atr_mult": {
      "quick": [0.5, 1.28]
    },
    "filter_tf": {
      "quick": ["2h", "4h"]
    },
    "trail_start_r": {
      "quick": [0.5, 0.91]
    },
    "trail_dist_r": {
      "quick": [0.015, 0.19]
    },
    "entry_validity_hours": {
      "quick": [12.0, 96.0]
    }
  }
}
```

### 백테스트 결과 비교

| 전략 | Sharpe | Win Rate | MDD | PF | Trades |
|------|--------|----------|-----|-----|--------|
| **[1] 보수적** | **33.01** | **97.7%** | **1.54%** | **134.76** | 4,457 |
| [2] 공격적 | 26.85 | 91.0% | 4.59% | 11.25 | 3,669 |
| [3] 혼합 | 31.51 | 96.3% | 1.54% | 66.86 | 4,447 |

**승자**: [1] 보수적 전략

---

## 4. 최적 파라미터 사용

```python
from core.strategy_core import AlphaX7Core

# Meta 최적 파라미터
params = {
    'atr_mult': 0.5,
    'filter_tf': '2h',
    'trail_start_r': 0.5,
    'trail_dist_r': 0.015,
    'entry_validity_hours': 12.0
}

# 전략 실행
strategy = AlphaX7Core(use_mtf=True)
trades = strategy.run_backtest(
    df_pattern=df,
    df_entry=df,
    slippage=0.0005,
    pattern_tolerance=0.05,
    enable_pullback=False,
    **params
)
```

---

## 5. 핵심 파일

| 파일 | 역할 |
|------|------|
| `config/meta_ranges.py` | 메타 범위 정의 (14,700 조합) |
| `core/meta_optimizer.py` | 메타 최적화 엔진 |
| `tools/test_meta_result.py` | 간단 백테스트 |
| `tools/compare_meta_params.py` | 파라미터 비교 |
| `presets/meta_ranges/*.json` | 최적화 결과 |

---

## 6. 요약

```
1. Meta 실행 (20초)
   → 14,700 조합 중 400개 샘플링
   → 최적 범위 자동 추출

2. 결과 확인
   → JSON 파일 생성
   → Quick 모드 범위 확인

3. 백테스트
   → Quick 시작값 (보수적)
   → Quick 끝값 (공격적)
   → 최고 성능 선택

4. 실전 적용
   → 최적 파라미터 사용
```

**시간**: 총 1분 (Meta 20초 + 백테스트 40초)

**결과**: Sharpe 33.01, 승률 97.7%, MDD 1.54%
