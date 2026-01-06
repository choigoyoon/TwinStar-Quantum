# 전략 추가 가이드

## 개요

TwinStar Quantum은 플러그인 방식의 전략 구조를 지원합니다.
새 전략을 추가하려면 `BaseStrategy`를 상속한 클래스를 만들면 됩니다.

## 빠른 시작

### 1. 새 전략 파일 생성

`strategies/my_strategy.py`:

```python
from strategies.base_strategy import BaseStrategy, Signal, register_strategy
import pandas as pd
from datetime import datetime

@register_strategy
class MyStrategy(BaseStrategy):
    """나만의 전략"""
    
    name = "my_strategy"        # 전략 식별자 (필수)
    version = "1.0.0"           # 버전
    
    # 기본 파라미터
    default_params = {
        'rsi_period': 14,
        'threshold': 70,
    }
    
    # 필수 파라미터 (없으면 에러)
    required_params = ['rsi_period']
    
    def check_signal(self, df_pattern, df_entry=None, **kwargs):
        """
        신호 확인 로직 (필수 구현)
        
        Args:
            df_pattern: 패턴용 데이터 (예: 4H)
            df_entry: 진입용 데이터 (예: 15m)
            
        Returns:
            Signal 객체 또는 None
        """
        # RSI 계산
        rsi = self._calculate_rsi(df_pattern, self.get_param('rsi_period'))
        
        # 신호 판단
        if rsi[-1] < 30:
            return Signal(
                timestamp=datetime.now(),
                signal_type='Long',
                entry_price=df_pattern['close'].iloc[-1],
                stop_loss=df_pattern['low'].iloc[-1] * 0.99,
                pattern='RSI_Oversold',
                confidence=0.8
            )
        elif rsi[-1] > 70:
            return Signal(
                timestamp=datetime.now(),
                signal_type='Short',
                entry_price=df_pattern['close'].iloc[-1],
                stop_loss=df_pattern['high'].iloc[-1] * 1.01,
                pattern='RSI_Overbought',
                confidence=0.8
            )
        
        return None
    
    def _calculate_rsi(self, df, period):
        """RSI 계산 헬퍼"""
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
```

### 2. 전략 등록 확인

```python
from strategies.base_strategy import StrategyRegistry

# 등록된 전략 목록
print(StrategyRegistry.list_all())
# ['alpha_x7', 'my_strategy', ...]

# 전략 인스턴스 생성
strategy = StrategyRegistry.create('my_strategy', {'threshold': 65})
print(strategy.describe())
```

### 3. 전략 사용

```python
# 신호 확인
signal = strategy.check_signal(df_4h, df_15m)

if signal:
    print(f"신호 발생: {signal.signal_type} @ {signal.entry_price}")
```

## BaseStrategy 메서드

### 필수 구현

| 메서드 | 설명 |
|--------|------|
| `check_signal(df_pattern, df_entry)` | 신호 확인 (Long/Short/None) |

### 선택 구현

| 메서드 | 설명 |
|--------|------|
| `run_backtest(df, start, end)` | 백테스트 최적화 버전 |

### 유틸리티

| 메서드 | 설명 |
|--------|------|
| `get_param(key, default)` | 파라미터 조회 |
| `set_param(key, value)` | 파라미터 설정 |
| `describe()` | 전략 정보 반환 |

## Signal 클래스

```python
@dataclass
class Signal:
    timestamp: datetime      # 신호 시각
    signal_type: str        # 'Long' 또는 'Short'
    entry_price: float      # 진입 가격
    stop_loss: float        # 손절가
    pattern: str            # 패턴명 (예: 'W', 'M', 'RSI')
    confidence: float       # 신뢰도 0~1
    metadata: Dict          # 추가 데이터
```

## 전략 파라미터

### default_params

기본 파라미터 값:

```python
default_params = {
    'rsi_period': 14,
    'atr_mult': 2.0,
    'max_trades': 3,
}
```

### required_params

필수 파라미터 목록 (없으면 에러):

```python
required_params = ['rsi_period', 'atr_mult']
```

## 팁

1. **성능**: 대량 데이터 처리 시 `run_backtest()` 오버라이드 권장
2. **테스트**: 백테스트로 충분히 검증 후 실매매 적용
3. **로깅**: `logging` 모듈 사용 (`print()` 대신)
4. **에러처리**: 예외 발생 시 None 반환 권장

## 기존 전략 참고

- `strategies/alpha_x7.py` - AlphaX7 전략 (W/M 패턴)
- `core/strategy_core.py` - 원본 전략 코어
