# 🚀 TwinStar-Quantum 개선 계획서 (Phase B/C/D)

**작성일**: 2026-01-15
**현재 점수**: 7.8/10
**목표 점수**: 8.5/10+
**예상 소요 기간**: 5-8일

---

## 📋 목차

1. [Phase B: API 통일 및 리팩토링](#phase-b-api-통일-및-리팩토링)
2. [Phase C: 테스트 및 안정화](#phase-c-테스트-및-안정화)
3. [Phase D: 성능 최적화 및 모니터링](#phase-d-성능-최적화-및-모니터링)
4. [실행 전략](#실행-전략)
5. [리스크 관리](#리스크-관리)

---

## Phase B: API 통일 및 리팩토링

**예상 소요**: 2-3일
**우선순위**: 🔥🔥🔥 CRITICAL

---

### 🎯 Track 1: API 반환값 통일 (최우선!)

#### 📌 현황
**문제**: `place_market_order()` 반환값 불일치
- Bybit, Binance: `OrderResult` (dataclass) 또는 `str` (order_id)
- OKX, BingX, Bitget, Upbit, Bithumb, Lighter: `bool`

**영향 범위**:
- `core/order_executor.py:199` - 임시 Hotfix 적용됨
- 호출부에서 타입 가정 불가 (런타임 에러 위험)

#### ✅ 작업 목록

##### Step 1: OrderResult 데이터클래스 강화 (1시간)
**파일**: `exchanges/base_exchange.py`

```python
@dataclass
class OrderResult:
    """주문 결과 (통일된 반환 타입)"""
    success: bool                    # 주문 성공 여부
    order_id: str | None = None      # 주문 ID
    filled_price: float | None = None # 체결 가격
    filled_qty: float | None = None   # 체결 수량
    error: str | None = None         # 에러 메시지
    timestamp: datetime | None = None # 체결 시간

    @classmethod
    def from_bool(cls, success: bool, error: str | None = None) -> 'OrderResult':
        """bool → OrderResult 변환 (하위 호환)"""
        return cls(success=success, error=error)

    @classmethod
    def from_order_id(cls, order_id: str) -> 'OrderResult':
        """order_id → OrderResult 변환 (하위 호환)"""
        return cls(success=True, order_id=order_id)

    def __bool__(self) -> bool:
        """Truthy 체크 지원"""
        return self.success
```

**테스트**:
```python
# tests/test_order_result.py
def test_order_result_truthy():
    assert OrderResult(success=True)  # Truthy
    assert not OrderResult(success=False)  # Falsy
```

---

##### Step 2: 거래소 어댑터 수정 (4-6시간)

**수정 대상 파일** (7개):
1. `exchanges/okx_exchange.py`
2. `exchanges/bingx_exchange.py`
3. `exchanges/bitget_exchange.py`
4. `exchanges/upbit_exchange.py`
5. `exchanges/bithumb_exchange.py`
6. `exchanges/lighter_exchange.py`
7. `exchanges/ccxt_exchange.py` (범용 어댑터)

**예시: OKX 수정**
```python
# Before ❌
def place_market_order(self, side: str, size: float, ...) -> bool:
    try:
        order = self.client.place_order(...)
        return True
    except Exception as e:
        logging.error(f"Order failed: {e}")
        return False

# After ✅
def place_market_order(self, side: str, size: float, ...) -> OrderResult:
    try:
        order = self.client.place_order(...)
        return OrderResult(
            success=True,
            order_id=order.get('orderId'),
            filled_price=float(order.get('avgPx', 0)),
            filled_qty=float(order.get('sz', 0)),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logging.error(f"Order failed: {e}")
        return OrderResult(success=False, error=str(e))
```

**자동화 스크립트** (선택 사항):
```python
# tools/refactor_order_return.py
"""
place_market_order() 반환값 자동 변환 도구
return True → return OrderResult(success=True)
return False → return OrderResult(success=False)
"""
```

---

##### Step 3: update_stop_loss() 통일 (2시간)

**현황**: 일부 거래소 `bool`, 일부 `OrderResult` 반환

**수정 대상**:
- 모든 거래소 어댑터의 `update_stop_loss()` → `OrderResult` 반환

---

##### Step 4: close_position() 통일 (2시간)

**현황**: 일부 거래소 `bool`, 일부 `dict` 반환

**수정 대상**:
- 모든 거래소 어댑터의 `close_position()` → `OrderResult` 반환

---

##### Step 5: order_executor.py Hotfix 제거 (30분)

**파일**: `core/order_executor.py`

```python
# Before ❌ (라인 199 임시 Hotfix)
result = exchange.place_market_order(...)
if isinstance(result, bool):
    result = OrderResult(success=result)

# After ✅
result = exchange.place_market_order(...)
# 항상 OrderResult 반환 보장
if result.success:
    logging.info(f"Order placed: {result.order_id}")
```

---

##### Step 6: 단위 테스트 작성 (2시간)

**파일**: `tests/test_exchange_api_parity.py`

```python
"""
거래소 API 반환값 통일성 테스트
모든 거래소가 동일한 타입 반환하는지 검증
"""

import pytest
from exchanges.base_exchange import OrderResult
from exchanges import (
    BybitExchange, BinanceExchange, OKXExchange,
    BitgetExchange, BingXExchange, UpbitExchange
)

@pytest.mark.parametrize("exchange_class", [
    BybitExchange, BinanceExchange, OKXExchange,
    BitgetExchange, BingXExchange, UpbitExchange
])
def test_place_market_order_returns_order_result(exchange_class):
    """place_market_order()가 OrderResult 반환하는지 검증"""
    exchange = exchange_class(api_key="test", secret="test", testnet=True)

    # Mock 또는 testnet 환경에서 실행
    result = exchange.place_market_order(side="Long", size=0.01, ...)

    assert isinstance(result, OrderResult)
    assert isinstance(result.success, bool)
    if result.success:
        assert result.order_id is not None

def test_order_result_truthy():
    """OrderResult가 bool 타입으로 평가되는지 검증"""
    assert OrderResult(success=True)  # Truthy
    assert not OrderResult(success=False)  # Falsy
```

---

#### 📊 Track 1 예상 결과

| 항목 | Before | After |
|------|--------|-------|
| **반환 타입 일관성** | 50% (2/9 거래소) | 100% (9/9 거래소) |
| **타입 안전성** | ⚠️ 런타임 체크 필요 | ✅ 컴파일 타임 보장 |
| **Hotfix 코드** | 있음 (order_executor:199) | 제거됨 |
| **테스트 커버리지** | 0% | 100% (9개 거래소) |

**예상 점수 향상**: 8.5/10 → 8.8/10 (+0.3)

---

### 🔧 Track 2: 리샘플링 SSOT 통합

**예상 소요**: 1-2일
**우선순위**: 🔥🔥 HIGH

#### 📌 현황
**문제**: 리샘플링 로직이 3곳에 중복 구현됨
1. `core/data_manager.py:258-295` (38줄)
2. `core/optimizer.py:710-739` (30줄)
3. `core/strategy_core.py:745-748` (복잡한 로직)

**목표**: `utils/data_utils.resample_data()` 단일 함수로 통합

---

#### ✅ 작업 목록

##### Step 1: utils/data_utils.py 강화 (2시간)

**파일**: `utils/data_utils.py`

```python
def resample_data(
    df: pd.DataFrame,
    target_tf: str,
    source_tf: str = '15m',
    add_indicators: bool = False,
    indicator_params: dict | None = None
) -> pd.DataFrame:
    """
    OHLCV 데이터 리샘플링 (SSOT)

    Args:
        df: 원본 데이터프레임 (15m 기준)
        target_tf: 목표 타임프레임 ('1h', '4h', '1d')
        source_tf: 원본 타임프레임 (기본값: '15m')
        add_indicators: 지표 자동 계산 여부
        indicator_params: 지표 파라미터

    Returns:
        리샘플링된 데이터프레임

    Examples:
        >>> df_15m = load_ohlcv('bybit', 'BTCUSDT', '15m')
        >>> df_1h = resample_data(df_15m, '1h')
        >>> df_4h = resample_data(df_15m, '4h', add_indicators=True)

    Note:
        - 타임존: UTC 강제
        - 타임스탬프: ms 정수 유지
        - 지표: RSI, ATR, MACD 자동 계산 가능
    """
    from config.constants import normalize_timeframe, TF_RESAMPLE_MAP
    from utils.indicators import calculate_rsi, calculate_atr, calculate_macd

    # 1. 타임프레임 정규화
    target_tf = normalize_timeframe(target_tf)

    # 2. 타임존 정규화
    if 'timestamp' not in df.columns:
        raise ValueError("DataFrame must have 'timestamp' column")

    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.set_index('timestamp', inplace=True)

    # 3. 리샘플링 규칙
    resample_rule = TF_RESAMPLE_MAP.get(target_tf, target_tf)

    # 4. OHLCV 리샘플링
    resampled = df.resample(resample_rule).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    # 5. 타임스탬프 복원 (ms 정수)
    resampled.reset_index(inplace=True)
    resampled['timestamp'] = (resampled['timestamp'].astype('int64') // 1_000_000).astype('int64')

    # 6. 지표 계산 (선택 사항)
    if add_indicators:
        params = indicator_params or {}

        # RSI
        rsi_period = params.get('rsi_period', 14)
        resampled['rsi'] = calculate_rsi(resampled['close'], period=rsi_period, return_series=True)

        # ATR
        atr_period = params.get('atr_period', 14)
        resampled['atr'] = calculate_atr(
            resampled['high'],
            resampled['low'],
            resampled['close'],
            period=atr_period,
            return_series=True
        )

        # MACD
        macd_fast = params.get('macd_fast', 12)
        macd_slow = params.get('macd_slow', 26)
        macd_signal = params.get('macd_signal', 9)
        macd_result = calculate_macd(
            resampled['close'],
            fast=macd_fast,
            slow=macd_slow,
            signal=macd_signal
        )
        resampled['macd'] = macd_result['macd']
        resampled['macd_signal'] = macd_result['signal']
        resampled['macd_hist'] = macd_result['histogram']

    return resampled
```

**테스트**:
```python
# tests/test_data_utils_resample.py
def test_resample_15m_to_1h():
    """15m → 1h 리샘플링 검증"""
    df_15m = create_sample_data(periods=100, freq='15min')
    df_1h = resample_data(df_15m, '1h')

    assert len(df_1h) == 25  # 100 / 4 = 25
    assert df_1h['timestamp'].dtype == 'int64'

def test_resample_with_indicators():
    """지표 자동 계산 검증"""
    df_15m = create_sample_data(periods=100, freq='15min')
    df_1h = resample_data(df_15m, '1h', add_indicators=True)

    assert 'rsi' in df_1h.columns
    assert 'atr' in df_1h.columns
    assert 'macd' in df_1h.columns
```

---

##### Step 2: core/data_manager.py 마이그레이션 (30분)

**파일**: `core/data_manager.py`

```python
# Before ❌ (라인 258-295)
def resample_data(self, df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """로컬 리샘플링 로직 (38줄)"""
    # ... 복잡한 로직

# After ✅
def resample_data(self, df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """리샘플링 (SSOT 위임)"""
    from utils.data_utils import resample_data as resample
    return resample(df, target_tf, source_tf='15m')
```

---

##### Step 3: core/optimizer.py 마이그레이션 (30분)

**파일**: `core/optimizer.py`

```python
# Before ❌ (라인 710-739)
def _resample(self, df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """로컬 리샘플링 로직 (30줄)"""
    # ... 복잡한 로직

# After ✅
def _resample(self, df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """리샘플링 (SSOT 위임)"""
    from utils.data_utils import resample_data
    return resample_data(df, target_tf, add_indicators=True)
```

---

##### Step 4: core/strategy_core.py 마이그레이션 (1시간)

**파일**: `core/strategy_core.py`

```python
# Before ❌ (라인 745-748)
df_4h = df_entry.resample('4H').agg(...)
df_1d = df_entry.resample('1D').agg(...)
# ... 복잡한 로직

# After ✅
from utils.data_utils import resample_data

df_4h = resample_data(df_entry, '4h', add_indicators=False)
df_1d = resample_data(df_entry, '1d', add_indicators=False)
```

---

##### Step 5: 회귀 테스트 실행 (1시간)

**테스트 대상**:
1. `tests/test_data_manager.py`
2. `tests/test_optimizer.py`
3. `tests/test_strategy_core.py`
4. `tests/test_integration_suite.py`

**검증 항목**:
- 리샘플링 결과 동일한지 확인
- 백테스트 메트릭 일치 여부
- 최적화 결과 변동 없음

---

#### 📊 Track 2 예상 결과

| 항목 | Before | After |
|------|--------|-------|
| **리샘플링 로직** | 3곳 중복 (100줄) | 1곳 (60줄) |
| **코드 중복** | 있음 | 제거됨 |
| **유지보수성** | 낮음 | 높음 (SSOT) |
| **테스트 커버리지** | 0% | 100% |

**예상 점수 향상**: 8.8/10 → 9.0/10 (+0.2)

---

### 🔗 Track 3: 임포트 패턴 통일

**예상 소요**: 2-4시간
**우선순위**: 🔥 MEDIUM

#### 📌 현황
**문제**: 임포트 패턴 불일치
- 일부 모듈: `from config.constants import TF_MAPPING`
- 일부 모듈: `from config.constants.timeframes import TF_MAPPING`

**목표**: `config/constants/__init__.py`에서 통합 export 사용

---

#### ✅ 작업 목록

##### Step 1: 임포트 패턴 검색 (30분)

**스크립트**: `tools/find_import_patterns.py`

```python
"""
프로젝트 전체 임포트 패턴 분석
일관되지 않은 임포트 찾기
"""

import re
from pathlib import Path

def find_inconsistent_imports(root_dir: str):
    pattern1 = re.compile(r'from config\.constants import')
    pattern2 = re.compile(r'from config\.constants\.\w+ import')

    results = {'pattern1': [], 'pattern2': []}

    for py_file in Path(root_dir).rglob('*.py'):
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue

        content = py_file.read_text(encoding='utf-8')

        if pattern1.search(content):
            results['pattern1'].append(str(py_file))
        if pattern2.search(content):
            results['pattern2'].append(str(py_file))

    return results

# 실행
results = find_inconsistent_imports('f:/TwinStar-Quantum')
print(f"Pattern 1 (권장): {len(results['pattern1'])}개 파일")
print(f"Pattern 2 (비권장): {len(results['pattern2'])}개 파일")
```

---

##### Step 2: 임포트 자동 변환 (1시간)

**스크립트**: `tools/refactor_imports.py`

```python
"""
임포트 패턴 자동 변환
from config.constants.timeframes import TF_MAPPING
→ from config.constants import TF_MAPPING
"""

import re
from pathlib import Path

def refactor_import(file_path: Path):
    content = file_path.read_text(encoding='utf-8')

    # Pattern: from config.constants.{module} import {names}
    pattern = r'from config\.constants\.(\w+) import (.+)'

    def replace_import(match):
        module = match.group(1)
        names = match.group(2)
        return f'from config.constants import {names}'

    new_content = re.sub(pattern, replace_import, content)

    if new_content != content:
        file_path.write_text(new_content, encoding='utf-8')
        return True
    return False

# 실행
for py_file in Path('f:/TwinStar-Quantum').rglob('*.py'):
    if refactor_import(py_file):
        print(f"✅ Refactored: {py_file}")
```

---

##### Step 3: config/constants/__init__.py 검증 (30분)

**파일**: `config/constants/__init__.py`

**확인 사항**:
1. 모든 서브모듈이 `__all__`에 포함되어 있는지
2. 순환 임포트 없는지
3. 타입 힌트 정확한지

---

##### Step 4: 프로젝트 전체 테스트 (1시간)

**테스트 실행**:
```bash
# 모든 테스트 실행
python -m pytest tests/ -v

# VS Code Problems 탭 확인
# Pyright 에러 0개 유지
```

---

#### 📊 Track 3 예상 결과

| 항목 | Before | After |
|------|--------|-------|
| **임포트 패턴** | 2가지 혼용 | 1가지 통일 |
| **가독성** | 보통 | 향상 |
| **순환 임포트 위험** | 있음 | 제거됨 |

---

## Phase C: 테스트 및 안정화

**예상 소요**: 2-3일
**우선순위**: 🔥🔥 HIGH

---

### 🧪 Track 1: 단위 테스트 추가

**예상 소요**: 2-3일
**우선순위**: 🔥🔥🔥 CRITICAL

#### 📌 현황
**문제**: 핵심 모듈 테스트 커버리지 낮음
- `core/optimizer.py`: 테스트 없음
- `core/strategy_core.py`: 테스트 없음
- `core/unified_bot.py`: 테스트 없음

**목표**: 80% 이상 코드 커버리지

---

#### ✅ 작업 목록

##### 1. core/optimizer.py 테스트 (6-8시간)

**파일**: `tests/test_optimizer.py`

```python
"""
core/optimizer.py 단위 테스트
그리드 생성, 메트릭 계산, 결과 분류 검증
"""

import pytest
from core.optimizer import Optimizer

class TestGridGeneration:
    """그리드 생성 테스트"""

    def test_generate_quick_grid(self):
        """Quick 모드 그리드 생성"""
        optimizer = Optimizer('bybit', 'BTCUSDT')
        grid = optimizer.generate_grid_by_mode('quick')

        assert len(grid) <= 150  # Quick: ~100 조합
        assert all(isinstance(params, dict) for params in grid)

    def test_generate_standard_grid(self):
        """Standard 모드 그리드 생성"""
        optimizer = Optimizer('bybit', 'BTCUSDT')
        grid = optimizer.generate_grid_by_mode('standard')

        assert 2000 <= len(grid) <= 5000  # Standard: ~3,000 조합

    def test_generate_deep_grid(self):
        """Deep 모드 그리드 생성"""
        optimizer = Optimizer('bybit', 'BTCUSDT')
        grid = optimizer.generate_grid_by_mode('deep')

        assert len(grid) >= 30000  # Deep: ~50,000 조합

class TestMetricsCalculation:
    """메트릭 계산 테스트"""

    def test_calculate_metrics(self):
        """백테스트 메트릭 계산"""
        trades = [
            {'entry_price': 100, 'exit_price': 110, 'side': 'Long', 'pnl': 10},
            {'entry_price': 110, 'exit_price': 105, 'side': 'Short', 'pnl': -5},
            {'entry_price': 105, 'exit_price': 115, 'side': 'Long', 'pnl': 10},
        ]

        metrics = Optimizer.calculate_metrics(trades, leverage=1)

        assert metrics['total_return'] == 15
        assert metrics['trade_count'] == 3
        assert 0 <= metrics['win_rate'] <= 100
        assert metrics['profit_factor'] > 0

class TestResultClassification:
    """결과 분류 테스트"""

    def test_classify_quick_results(self):
        """Quick 모드 결과 분류"""
        results = [
            {'params': {...}, 'total_return': 100, 'win_rate': 80, 'mdd': 10},
            {'params': {...}, 'total_return': 80, 'win_rate': 75, 'mdd': 15},
        ]

        classified = Optimizer._classify_results(results, mode='quick')

        assert 'optimal' in classified
        assert len(classified) == 1  # Quick: 최적 1개

    def test_classify_standard_results(self):
        """Standard 모드 결과 분류"""
        results = [...]
        classified = Optimizer._classify_results(results, mode='standard')

        assert 'aggressive' in classified
        assert 'balanced' in classified
        assert 'conservative' in classified
```

**예상 테스트 수**: 30개 이상

---

##### 2. core/strategy_core.py 테스트 (6-8시간)

**파일**: `tests/test_strategy_core.py`

```python
"""
core/strategy_core.py 단위 테스트
W/M 패턴 감지, 백테스트 실행 검증
"""

import pytest
from core.strategy_core import AlphaX7Core

class TestPatternDetection:
    """W/M 패턴 감지 테스트"""

    def test_detect_w_pattern(self):
        """W 패턴 감지"""
        df = create_sample_w_pattern()  # Helper 함수
        strategy = AlphaX7Core()

        pattern = strategy._detect_wm_pattern(df, pattern_type='W')

        assert pattern is not None
        assert pattern['type'] == 'W'
        assert 'confidence' in pattern

    def test_detect_m_pattern(self):
        """M 패턴 감지"""
        df = create_sample_m_pattern()
        strategy = AlphaX7Core()

        pattern = strategy._detect_wm_pattern(df, pattern_type='M')

        assert pattern is not None
        assert pattern['type'] == 'M'

class TestMTFFilter:
    """MTF 필터 테스트"""

    def test_mtf_aligned_long(self):
        """MTF 정렬 (Long)"""
        df_4h = create_uptrend_data()
        df_1d = create_uptrend_data()

        strategy = AlphaX7Core()
        aligned = strategy._check_mtf_alignment(df_4h, df_1d, direction='Long')

        assert aligned is True

    def test_mtf_not_aligned(self):
        """MTF 불일치"""
        df_4h = create_uptrend_data()
        df_1d = create_downtrend_data()

        strategy = AlphaX7Core()
        aligned = strategy._check_mtf_alignment(df_4h, df_1d, direction='Long')

        assert aligned is False

class TestBacktestExecution:
    """백테스트 실행 테스트"""

    def test_run_backtest_basic(self):
        """기본 백테스트 실행"""
        df = load_sample_data()
        strategy = AlphaX7Core()

        result = strategy.run_backtest(df, params=DEFAULT_PARAMS, leverage=1)

        assert 'total_return' in result
        assert 'trade_count' in result
        assert result['trade_count'] >= 0

    def test_run_backtest_with_slippage(self):
        """슬리피지 적용 백테스트"""
        df = load_sample_data()
        strategy = AlphaX7Core()

        result = strategy.run_backtest(df, params=DEFAULT_PARAMS, slippage=0.001)

        # 슬리피지 적용 시 수익률 감소
        result_no_slippage = strategy.run_backtest(df, params=DEFAULT_PARAMS, slippage=0)
        assert result['total_return'] < result_no_slippage['total_return']
```

**예상 테스트 수**: 25개 이상

---

##### 3. core/unified_bot.py 테스트 (4-6시간)

**파일**: `tests/test_unified_bot.py`

```python
"""
core/unified_bot.py 단위 테스트
시그널 감지, 포지션 관리 검증
"""

import pytest
from unittest.mock import Mock, patch
from core.unified_bot import UnifiedBot

class TestSignalDetection:
    """시그널 감지 테스트"""

    @patch('core.unified_bot.BotDataManager')
    def test_detect_signal_long(self, mock_data_manager):
        """Long 시그널 감지"""
        mock_data_manager.get_recent_data.return_value = create_long_signal_data()

        bot = UnifiedBot('bybit', 'BTCUSDT', testnet=True)
        signal = bot.detect_signal()

        assert signal is not None
        assert signal['direction'] == 'Long'
        assert signal['confidence'] > 0

    def test_detect_signal_no_signal(self):
        """시그널 없음"""
        bot = UnifiedBot('bybit', 'BTCUSDT', testnet=True)

        # 노이즈 데이터
        with patch.object(bot.mod_data, 'get_recent_data', return_value=create_noise_data()):
            signal = bot.detect_signal()
            assert signal is None

class TestPositionManagement:
    """포지션 관리 테스트"""

    def test_manage_position_trailing_sl(self):
        """트레일링 SL 업데이트"""
        bot = UnifiedBot('bybit', 'BTCUSDT', testnet=True)
        bot.mod_state.has_position = True
        bot.mod_state.current_position = Mock(entry_price=100, stop_loss=95)

        # 가격 상승 시 SL 업데이트
        with patch.object(bot.exchange, 'get_current_price', return_value=110):
            bot.manage_position()

            # SL이 상승했는지 확인
            assert bot.mod_state.current_position.stop_loss > 95

class TestThreadSafety:
    """스레드 안전성 테스트"""

    def test_data_lock(self):
        """데이터 Lock 검증"""
        bot = UnifiedBot('bybit', 'BTCUSDT', testnet=True)

        assert hasattr(bot.mod_data, '_data_lock')
        assert isinstance(bot.mod_data._data_lock, threading.RLock)

    def test_position_lock(self):
        """포지션 Lock 검증"""
        bot = UnifiedBot('bybit', 'BTCUSDT', testnet=True)

        assert hasattr(bot, '_position_lock')
        assert isinstance(bot._position_lock, threading.RLock)
```

**예상 테스트 수**: 20개 이상

---

#### 📊 Track 1 예상 결과

| 모듈 | Before | After |
|------|--------|-------|
| **core/optimizer.py** | 0% 커버리지 | 80%+ 커버리지 |
| **core/strategy_core.py** | 0% 커버리지 | 75%+ 커버리지 |
| **core/unified_bot.py** | 0% 커버리지 | 70%+ 커버리지 |
| **전체 테스트 수** | 46개 | 120개+ |

**예상 점수 향상**: 9.0/10 → 9.2/10 (+0.2)

---

### 🔗 Track 2: 통합 테스트 강화

**예상 소요**: 1-2일
**우선순위**: 🔥🔥 HIGH

#### 📌 현황
**문제**: 통합 테스트 부족
- Phase A-1 (WebSocket 연동) 통합 테스트 미흡
- Phase A-2 (메모리 vs 히스토리) 통합 테스트 미흡
- 백테스트 vs 실시간 parity 테스트 없음

**목표**: End-to-End 시나리오 검증

---

#### ✅ 작업 목록

##### 1. Phase A 통합 테스트 (4시간)

**파일**: `tests/test_phase_a_integration.py`

```python
"""
Phase A (WebSocket + 메모리) 통합 테스트
실시간 데이터 수집 → 저장 → 백테스트 플로우 검증
"""

import pytest
from core.data_manager import BotDataManager
from exchanges.ws_handler import WebSocketHandler

class TestWebSocketIntegration:
    """WebSocket 통합 테스트"""

    @pytest.mark.integration
    def test_websocket_to_parquet(self):
        """WebSocket → Parquet 저장 플로우"""
        manager = BotDataManager('bybit', 'BTCUSDT')
        ws = WebSocketHandler('bybit', 'BTCUSDT', '15m')

        candles_received = []

        def on_candle_close(candle):
            candles_received.append(candle)
            manager.append_candle(candle)

        ws.on_candle_close = on_candle_close
        ws.start()

        # 5분 대기 (최소 1개 봉 마감)
        time.sleep(300)

        ws.stop()

        # 검증
        assert len(candles_received) >= 1
        assert manager.get_entry_file_path().exists()

        # Parquet 로드
        df = pd.read_parquet(manager.get_entry_file_path())
        assert len(df) >= 1

class TestMemoryHistorySeparation:
    """메모리 vs 히스토리 분리 테스트"""

    def test_get_recent_data_warmup(self):
        """워밍업 윈도우 적용 검증"""
        manager = BotDataManager('bybit', 'BTCUSDT')

        # 샘플 데이터 로드 (200개 이상)
        manager.load_historical()

        # 최근 100개 + 워밍업 100개
        df_recent = manager.get_recent_data(limit=100, warmup_window=100)

        assert len(df_recent) == 200

        # 지표 계산 (워밍업 포함)
        from utils.indicators import calculate_rsi
        rsi = calculate_rsi(df_recent['close'], period=14, return_series=True)

        # 워밍업 구간은 NaN, 실제 데이터는 정상
        assert rsi.iloc[:14].isna().all()  # 워밍업
        assert rsi.iloc[100:].notna().all()  # 실제 데이터
```

---

##### 2. 백테스트 vs 실시간 parity 테스트 (4시간)

**파일**: `tests/test_backtest_realtime_parity.py`

```python
"""
백테스트 vs 실시간 매매 parity 테스트
동일한 데이터, 동일한 파라미터 → 동일한 결과
"""

import pytest
from core.strategy_core import AlphaX7Core
from core.unified_bot import UnifiedBot

class TestBacktestRealtimeParity:
    """백테스트 vs 실시간 parity"""

    def test_signal_detection_parity(self):
        """시그널 감지 일치 검증"""
        df = load_sample_data()
        params = DEFAULT_PARAMS

        # 백테스트 시그널
        strategy = AlphaX7Core()
        backtest_signals = []

        for i in range(100, len(df)):
            df_slice = df.iloc[:i]
            signal = strategy.check_signal(df_slice, params)
            if signal:
                backtest_signals.append((i, signal))

        # 실시간 시뮬레이션
        bot = UnifiedBot('bybit', 'BTCUSDT', testnet=True)
        realtime_signals = []

        for i in range(100, len(df)):
            # 메모리 상태 시뮬레이션
            df_slice = df.iloc[max(0, i-200):i]
            df_recent = bot.mod_data.get_recent_data_from_df(df_slice, limit=100, warmup=100)

            signal = bot.detect_signal_from_df(df_recent)
            if signal:
                realtime_signals.append((i, signal))

        # 일치율 검증 (100% 일치)
        assert len(backtest_signals) == len(realtime_signals)

        for (bt_idx, bt_signal), (rt_idx, rt_signal) in zip(backtest_signals, realtime_signals):
            assert bt_idx == rt_idx
            assert bt_signal['direction'] == rt_signal['direction']
```

---

#### 📊 Track 2 예상 결과

| 항목 | Before | After |
|------|--------|-------|
| **통합 테스트 수** | 2개 | 10개+ |
| **End-to-End 커버리지** | 0% | 80%+ |
| **백테스트 parity** | 미검증 | 검증 완료 |

---

### 🛡️ Track 3: 타입 안전성 강화

**예상 소요**: 2-4시간
**우선순위**: 🔥 MEDIUM

#### ✅ 작업 목록

##### 1. 타입 힌트 추가 (2시간)

**대상 파일**:
- `core/order_executor.py`
- `core/position_manager.py`
- `core/signal_processor.py`

**예시**:
```python
# Before ❌
def calculate_pnl(entry_price, exit_price, side, size):
    ...

# After ✅
def calculate_pnl(
    entry_price: float,
    exit_price: float,
    side: str,
    size: float,
    leverage: int = 1
) -> tuple[float, float]:
    """PnL 계산 (수수료 차감)"""
    ...
```

---

##### 2. Optional 타입 명시 (1시간)

**예시**:
```python
# Before ❌
def get_position() -> Position:
    ...

# After ✅
def get_position() -> Position | None:
    """현재 포지션 조회 (없으면 None)"""
    ...
```

---

##### 3. Pyright 에러 0개 유지 (1시간)

**검증**:
```bash
# VS Code Problems 탭 확인
# Pyright: 0 errors, 0 warnings
```

---

#### 📊 Track 3 예상 결과

| 항목 | Before | After |
|------|--------|-------|
| **타입 힌트 커버리지** | 70% | 95%+ |
| **Pyright 에러** | 0개 (유지) | 0개 (유지) |
| **Optional 타입** | 부분 명시 | 완전 명시 |

**예상 점수 향상**: 9.2/10 → 9.3/10 (+0.1)

---

## Phase D: 성능 최적화 및 모니터링

**예상 소요**: 1-2일
**우선순위**: 🔥 MEDIUM

---

### 📊 Track 1: 성능 프로파일링

**예상 소요**: 4-6시간
**우선순위**: 🔥🔥 HIGH

#### ✅ 작업 목록

##### 1. core/optimizer.py 성능 측정 (2시간)

**스크립트**: `tools/profile_optimizer.py`

```python
"""
core/optimizer.py 성능 프로파일링
병렬 처리 효율 측정
"""

import cProfile
import pstats
from core.optimizer import Optimizer

def profile_optimizer():
    optimizer = Optimizer('bybit', 'BTCUSDT')

    # Quick 모드 프로파일링
    profiler = cProfile.Profile()
    profiler.enable()

    results = optimizer.run_optimization(mode='quick')

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)

if __name__ == '__main__':
    profile_optimizer()
```

**측정 항목**:
- 그리드 생성 시간
- 백테스트 실행 시간 (단일/병렬)
- 메트릭 계산 시간
- 메모리 사용량

---

##### 2. core/data_manager.py I/O 성능 (2시간)

**스크립트**: `tools/profile_data_io.py`

```python
"""
Parquet I/O 성능 측정
읽기/쓰기 속도 벤치마크
"""

import time
from core.data_manager import BotDataManager

def benchmark_parquet_io():
    manager = BotDataManager('bybit', 'BTCUSDT')

    # 읽기 성능
    start = time.time()
    df = manager.load_historical()
    read_time = time.time() - start

    print(f"Read time: {read_time*1000:.2f}ms ({len(df)} rows)")

    # 쓰기 성능
    start = time.time()
    manager.save_parquet()
    write_time = time.time() - start

    print(f"Write time: {write_time*1000:.2f}ms")

if __name__ == '__main__':
    benchmark_parquet_io()
```

---

##### 3. core/strategy_core.py 백테스트 속도 (2시간)

**스크립트**: `tools/profile_backtest.py`

```python
"""
백테스트 실행 속도 측정
10,000 candles 기준 벤치마크
"""

import time
from core.strategy_core import AlphaX7Core

def benchmark_backtest():
    df = load_sample_data(rows=10000)
    strategy = AlphaX7Core()

    start = time.time()
    result = strategy.run_backtest(df, params=DEFAULT_PARAMS)
    elapsed = time.time() - start

    print(f"Backtest time: {elapsed:.2f}s ({len(df)} candles)")
    print(f"Speed: {len(df)/elapsed:.0f} candles/sec")

if __name__ == '__main__':
    benchmark_backtest()
```

---

#### 📊 Track 1 예상 결과

| 모듈 | 현재 성능 | 목표 성능 |
|------|----------|----------|
| **optimizer.py** | Quick 2-3분 | Quick 1-2분 |
| **data_manager.py** | Read 5-15ms | Read 5-10ms |
| **strategy_core.py** | 100 candles/sec | 200 candles/sec |

---

### 📡 Track 2: 모니터링 추가

**예상 소요**: 4-6시간
**우선순위**: 🔥 MEDIUM

#### ✅ 작업 목록

##### 1. WebSocket 연결 상태 모니터링 (2시간)

**파일**: `core/unified_bot.py`

```python
def _monitor_websocket(self):
    """WebSocket 연결 상태 모니터링 (별도 스레드)"""
    while self.is_running:
        if not self.ws_handler.is_healthy(timeout=30):
            logging.warning("[BOT] WebSocket unhealthy, restarting...")
            self.ws_handler.stop()
            time.sleep(5)
            self._start_websocket()

        time.sleep(60)  # 1분마다 체크
```

---

##### 2. 데이터 갭 감지 및 알림 (2시간)

**파일**: `core/data_manager.py`

```python
def detect_data_gap(self, threshold_minutes: int = 60) -> list[tuple[datetime, datetime]]:
    """
    데이터 갭 감지

    Args:
        threshold_minutes: 갭 임계값 (기본: 60분)

    Returns:
        갭 구간 리스트 [(start, end), ...]
    """
    df = self.load_historical()

    if len(df) < 2:
        return []

    df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df['time_diff'] = df['timestamp_dt'].diff()

    gaps = df[df['time_diff'] > pd.Timedelta(minutes=threshold_minutes)]

    gap_list = []
    for idx, row in gaps.iterrows():
        start = df.loc[idx-1, 'timestamp_dt']
        end = row['timestamp_dt']
        gap_list.append((start, end))

    return gap_list
```

---

##### 3. 메모리 사용량 추적 (2시간)

**파일**: `utils/memory_monitor.py`

```python
"""
메모리 사용량 추적 모듈
"""

import psutil
import logging

class MemoryMonitor:
    """메모리 사용량 모니터"""

    def __init__(self, threshold_mb: int = 500):
        self.threshold_mb = threshold_mb
        self.process = psutil.Process()

    def check_memory(self) -> dict:
        """메모리 사용량 체크"""
        mem_info = self.process.memory_info()
        mem_mb = mem_info.rss / 1024 / 1024

        if mem_mb > self.threshold_mb:
            logging.warning(f"[MEMORY] High usage: {mem_mb:.1f}MB")

        return {
            'rss_mb': mem_mb,
            'vms_mb': mem_info.vms / 1024 / 1024,
            'percent': self.process.memory_percent()
        }
```

---

#### 📊 Track 2 예상 결과

| 항목 | Before | After |
|------|--------|-------|
| **WebSocket 모니터링** | 없음 | 1분마다 체크 |
| **데이터 갭 감지** | 없음 | 자동 감지 + 알림 |
| **메모리 추적** | 없음 | 임계값 알림 |

---

### 🛠️ Track 3: 에러 처리 강화

**예상 소요**: 2-4시간
**우선순위**: 🔥 MEDIUM

#### ✅ 작업 목록

##### 1. 거래소 API 에러 핸들링 통일 (2시간)

**파일**: `exchanges/base_exchange.py`

```python
class ExchangeAPIError(Exception):
    """거래소 API 에러 기본 클래스"""
    pass

class RateLimitError(ExchangeAPIError):
    """Rate Limit 초과"""
    pass

class AuthenticationError(ExchangeAPIError):
    """인증 실패"""
    pass

class InsufficientBalanceError(ExchangeAPIError):
    """잔고 부족"""
    pass

def handle_api_error(func):
    """API 에러 핸들링 데코레이터"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ccxt.RateLimitExceeded as e:
            raise RateLimitError(f"Rate limit exceeded: {e}")
        except ccxt.AuthenticationError as e:
            raise AuthenticationError(f"Authentication failed: {e}")
        except ccxt.InsufficientFunds as e:
            raise InsufficientBalanceError(f"Insufficient balance: {e}")
        except Exception as e:
            logging.error(f"API error: {e}")
            raise ExchangeAPIError(f"Unexpected error: {e}")

    return wrapper
```

**적용**:
```python
class BybitExchange(BaseExchange):
    @handle_api_error
    def place_market_order(self, ...) -> OrderResult:
        ...
```

---

##### 2. 자동 복구 메커니즘 (2시간)

**파일**: `core/unified_bot.py`

```python
def _auto_recover(self, error: Exception):
    """에러 자동 복구"""
    if isinstance(error, RateLimitError):
        logging.warning("[BOT] Rate limit, sleeping 60s...")
        time.sleep(60)
        return True

    elif isinstance(error, AuthenticationError):
        logging.error("[BOT] Authentication failed, stopping...")
        self.stop()
        return False

    elif isinstance(error, InsufficientBalanceError):
        logging.warning("[BOT] Insufficient balance, reducing size...")
        # 포지션 사이즈 감소 로직
        return True

    else:
        logging.error(f"[BOT] Unhandled error: {error}")
        return False
```

---

#### 📊 Track 3 예상 결과

| 항목 | Before | After |
|------|--------|-------|
| **에러 핸들링** | 개별 구현 | 통일된 체계 |
| **자동 복구** | 없음 | Rate Limit, Balance 등 |
| **에러 분류** | Generic | 4개 타입 |

**예상 점수 향상**: 9.3/10 → 9.5/10 (+0.2)

---

## 실행 전략

### 🎯 작업 순서 (권장)

#### Week 1: Phase B (API 통일 및 리팩토링)
- **Day 1-2**: Track 1 (API 반환값 통일) ← 최우선!
- **Day 3**: Track 2 (리샘플링 SSOT 통합)
- **Day 4**: Track 3 (임포트 패턴 통일)

#### Week 2: Phase C (테스트 및 안정화)
- **Day 5-6**: Track 1 (단위 테스트 추가)
- **Day 7**: Track 2 (통합 테스트 강화)
- **Day 8**: Track 3 (타입 안전성 강화)

#### Week 3: Phase D (성능 최적화)
- **Day 9**: Track 1 (성능 프로파일링)
- **Day 10**: Track 2 (모니터링 추가)
- **Day 11**: Track 3 (에러 처리 강화)

---

### 📅 마일스톤

| 마일스톤 | 완료 조건 | 예상 점수 |
|---------|----------|----------|
| **M1: API 통일** | 9개 거래소 OrderResult 반환 | 8.8/10 |
| **M2: SSOT 통합** | 리샘플링 로직 단일화 | 9.0/10 |
| **M3: 테스트 강화** | 80%+ 코드 커버리지 | 9.3/10 |
| **M4: 최적화 완료** | 성능 향상 + 모니터링 | 9.5/10 |

---

## 리스크 관리

### 🚨 High Risk

#### 1. API 반환값 통일 시 호환성 깨짐
**리스크**: 기존 코드에서 `bool` 타입 가정 부분 런타임 에러

**대응**:
- `OrderResult.__bool__()` 메서드로 Truthy 체크 지원
- 회귀 테스트 철저히 실행
- 단계적 마이그레이션 (거래소별 1개씩)

---

#### 2. 리샘플링 로직 변경 시 결과 차이
**리스크**: 백테스트 결과 변동으로 신뢰성 저하

**대응**:
- 기존 로직과 새 로직 결과 비교 (diff < 0.1%)
- 샘플 데이터로 회귀 테스트
- 문제 발생 시 롤백 가능하도록 브랜치 관리

---

### ⚠️ Medium Risk

#### 3. 테스트 작성 시간 초과
**리스크**: 단위 테스트 작성이 예상보다 오래 걸림

**대응**:
- 핵심 모듈 우선 (optimizer, strategy_core)
- 커버리지 목표 80% → 70%로 조정 가능
- 통합 테스트는 최소한으로 유지

---

#### 4. 성능 프로파일링 결과 미흡
**리스크**: 성능 개선이 기대만큼 안 됨

**대응**:
- Phase D는 선택 사항으로 간주
- 병목 지점만 개선 (Quick wins)
- 대규모 리팩토링 지양

---

### 💡 Low Risk

#### 5. 임포트 패턴 통일 시 순환 임포트
**리스크**: `config/constants/__init__.py` 순환 임포트 발생

**대응**:
- 이미 `__init__.py`에서 통합 export 중
- 순환 임포트 발생 시 지연 임포트 (lazy import) 사용

---

## 📊 최종 예상 결과

### Phase B 완료 후
- **점수**: 7.8/10 → 9.0/10 (+1.2)
- **API 일관성**: 100%
- **코드 중복**: -60줄
- **SSOT 준수**: 95%

### Phase C 완료 후
- **점수**: 9.0/10 → 9.3/10 (+0.3)
- **테스트 커버리지**: 80%+
- **통합 테스트**: 10개+
- **타입 안전성**: 95%+

### Phase D 완료 후
- **점수**: 9.3/10 → 9.5/10 (+0.2)
- **성능**: +30% 향상
- **모니터링**: 완비
- **에러 핸들링**: 통일

---

## 🎉 결론

본 계획서를 완료하면 **TwinStar-Quantum** 프로젝트는:

✅ **API 일관성**: 100% 통일 (OrderResult 기반)
✅ **SSOT 준수**: 95%+ (리샘플링, 메트릭 통합)
✅ **테스트 커버리지**: 80%+ (120개+ 테스트)
✅ **성능**: 30% 향상 (병렬 처리 개선)
✅ **모니터링**: WebSocket, 데이터 갭, 메모리
✅ **에러 핸들링**: 통일된 체계

**최종 점수**: **9.5/10** 🚀

**프로덕션 준비도**: **95%+** (소액 실거래 및 Testnet 배포 권장)

---

**작성**: Claude Sonnet 4.5
**일자**: 2026-01-15
**예상 완료일**: 2026-01-26 (11일 후)
