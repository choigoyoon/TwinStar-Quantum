# 🔗 TwinStar Quantum - 추가 연동 가이드

> **버전**: v1.8.3  
> **업데이트**: 2026-01-13  
> **목적**: 새로운 기능 추가 및 모듈 연동 방법 가이드

---

## 📋 목차

1. [새 거래소 추가](#1-새-거래소-추가)
2. [새 전략 추가](#2-새-전략-추가)
3. [새 GUI 위젯 추가](#3-새-gui-위젯-추가)
4. [새 웹 탭 추가](#4-새-웹-탭-추가)
5. [새 알림 채널 추가](#5-새-알림-채널-추가)
6. [새 지표 추가](#6-새-지표-추가)

---

## 1️⃣ 새 거래소 추가

### 파일 구조

```
exchanges/
├── base_exchange.py      # 상속할 기본 클래스
├── new_exchange.py       # 새 거래소 어댑터
└── exchange_manager.py   # 여기에 등록
```

### 구현 단계

#### Step 1: 어댑터 파일 생성

```python
# exchanges/new_exchange.py
"""
NewExchange 거래소 어댑터
- 유형: 선물/현물
- API: ccxt 또는 공식 SDK
"""

from exchanges.base_exchange import BaseExchange
import ccxt

class NewExchange(BaseExchange):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        super().__init__()
        self.exchange = ccxt.newexchange({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        if testnet:
            self.exchange.set_sandbox_mode(True)
    
    def get_balance(self) -> dict:
        """잔고 조회"""
        balance = self.exchange.fetch_balance()
        return {'total': balance['total']['USDT'], 'free': balance['free']['USDT']}
    
    def place_order(self, symbol: str, side: str, amount: float, 
                    order_type: str = 'market', price: float = None) -> dict:
        """주문 실행"""
        return self.exchange.create_order(symbol, order_type, side, amount, price)
    
    def get_positions(self) -> list:
        """포지션 조회"""
        return self.exchange.fetch_positions()
    
    def close_position(self, symbol: str) -> dict:
        """포지션 청산"""
        # 구현
        pass
```

#### Step 2: ExchangeManager에 등록

```python
# exchanges/exchange_manager.py

from exchanges.new_exchange import NewExchange

EXCHANGE_MAP = {
    'bybit': BybitExchange,
    'binance': BinanceExchange,
    # ... 기존 거래소
    'newexchange': NewExchange,  # 추가
}
```

#### Step 3: WebSocket 지원 (선택)

```python
# exchanges/ws_handler.py

WS_ENDPOINTS = {
    # ... 기존 거래소
    'newexchange': 'wss://stream.newexchange.com/ws',
}

INTERVAL_MAP = {
    # ... 기존 거래소
    'newexchange': {'1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h'},
}
```

#### Step 4: GUI에 추가

```python
# GUI/settings_widget.py 또는 GUI/exchange_selector_widget.py

SUPPORTED_EXCHANGES = ['bybit', 'binance', ..., 'newexchange']
```

---

## 2️⃣ 새 전략 추가

### 파일 구조

```
strategies/
├── base_strategy.py       # 상속할 기본 클래스
├── new_strategy.py        # 새 전략
└── strategy_loader.py     # 여기에 등록
```

### 구현 단계

#### Step 1: 전략 파일 생성

```python
# strategies/new_strategy.py
"""
새로운 매매 전략
- 진입 조건: ...
- 청산 조건: ...
"""

from strategies.base_strategy import BaseStrategy
from dataclasses import dataclass
from typing import Optional
import pandas as pd

@dataclass
class NewStrategyParams:
    """전략 파라미터"""
    param1: int = 14
    param2: float = 1.5
    param3: bool = True

class NewStrategy(BaseStrategy):
    def __init__(self, params: NewStrategyParams = None):
        super().__init__()
        self.params = params or NewStrategyParams()
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[dict]:
        """신호 생성"""
        # 1. 지표 계산
        # 2. 조건 체크
        # 3. 신호 반환
        if self._check_entry_condition(df):
            return {
                'side': 'long',  # or 'short'
                'entry_price': df['close'].iloc[-1],
                'stop_loss': self._calc_stop_loss(df),
                'take_profit': self._calc_take_profit(df),
            }
        return None
    
    def _check_entry_condition(self, df: pd.DataFrame) -> bool:
        """진입 조건 체크"""
        # 구현
        return False
    
    def _calc_stop_loss(self, df: pd.DataFrame) -> float:
        """손절가 계산"""
        # 구현
        pass
    
    def _calc_take_profit(self, df: pd.DataFrame) -> float:
        """익절가 계산"""
        # 구현
        pass
```

#### Step 2: strategy_loader에 등록

```python
# strategies/strategy_loader.py

from strategies.new_strategy import NewStrategy

STRATEGY_MAP = {
    'alphax7': AlphaX7Core,
    'wm_pattern': WMPatternStrategy,
    'new_strategy': NewStrategy,  # 추가
}

def load_strategy(name: str, params: dict = None):
    """전략 로드"""
    if name not in STRATEGY_MAP:
        raise ValueError(f"Unknown strategy: {name}")
    return STRATEGY_MAP[name](params)
```

#### Step 3: 최적화 그리드 추가 (선택)

```python
# core/optimizer.py

def generate_new_strategy_grid():
    """새 전략 최적화 그리드"""
    return {
        'param1': [10, 14, 20],
        'param2': [1.0, 1.5, 2.0],
        'param3': [True, False],
    }
```

---

## 3️⃣ 새 GUI 위젯 추가

### 파일 구조

```
GUI/
├── new_widget.py          # 새 위젯
├── staru_main.py          # 메인 윈도우에 탭 추가
└── __init__.py            # import 등록
```

### 구현 단계

#### Step 1: 위젯 파일 생성

```python
# GUI/new_widget.py
"""
새 기능 위젯
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import pyqtSignal

class NewWidget(QWidget):
    # 시그널 정의 (다른 위젯과 통신용)
    data_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 스타일 적용
        self.setStyleSheet("""
            QWidget { background: #131722; }
            QLabel { color: white; }
            QPushButton {
                background: #2962FF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
        """)
        
        # UI 구성요소
        self.title = QLabel("새 기능")
        layout.addWidget(self.title)
        
        self.action_btn = QPushButton("실행")
        self.action_btn.clicked.connect(self._on_action)
        layout.addWidget(self.action_btn)
    
    def _on_action(self):
        """버튼 클릭 핸들러"""
        # 로직 실행
        result = {'status': 'success'}
        self.data_changed.emit(result)
```

#### Step 2: 메인 윈도우에 탭 추가

```python
# GUI/staru_main.py

from GUI.new_widget import NewWidget

class StarUWindow(QMainWindow):
    def _init_tabs(self):
        # ... 기존 탭들
        
        # 새 탭 추가
        self.new_widget = NewWidget()
        self.tabs.addTab(self.new_widget, "🆕 새 기능")
```

---

## 4️⃣ 새 웹 탭 추가

### 파일 구조

```
web/frontend/
├── index.html             # Vue.js SPA (여기에 추가)
└── guide_data.js          # 데이터 파일 (참고)
```

### 구현 단계

#### Step 1: 탭 정의 추가

```javascript
// web/frontend/index.html - tabs 배열에 추가

const tabs = [
    // ... 기존 탭들
    { id: 'newtab', name: '새 기능', icon: '🆕' },
];
```

#### Step 2: 탭 콘텐츠 추가

```html
<!-- web/frontend/index.html - main 태그 안에 추가 -->

<!-- ==================== 새 기능 탭 ==================== -->
<div v-show="activeTab === 'newtab'" class="space-y-6">
    <div class="card p-6">
        <h3 class="text-lg font-semibold mb-4">🆕 새 기능</h3>
        
        <!-- 설정 영역 -->
        <div class="space-y-4">
            <div>
                <label class="text-sm text-gray-400">옵션 1</label>
                <input type="text" v-model="newFeature.option1" 
                       class="input-field w-full px-4 py-2 rounded-lg">
            </div>
            
            <button @click="executeNewFeature" 
                    class="btn-primary text-white py-3 rounded-lg font-semibold w-full">
                실행
            </button>
        </div>
        
        <!-- 결과 영역 -->
        <div v-if="newFeature.result" class="mt-6 p-4 bg-[#1a1a24] rounded-lg">
            <h4 class="font-semibold mb-2">결과</h4>
            <div class="text-gray-300">{{ newFeature.result }}</div>
        </div>
    </div>
</div>
```

#### Step 3: 상태 및 함수 추가

```javascript
// web/frontend/index.html - setup() 함수 안에 추가

// 새 기능 상태
const newFeature = reactive({
    option1: '',
    result: null
});

// 새 기능 실행 함수
const executeNewFeature = () => {
    addLog('새 기능 실행 중...', 'info');
    // API 호출 또는 로직 실행
    newFeature.result = '실행 완료!';
    showToast('완료', 'success');
};

// return 문에 추가
return {
    // ... 기존 항목들
    newFeature,
    executeNewFeature,
};
```

---

## 5️⃣ 새 알림 채널 추가

### 파일 구조

```
├── new_notifier.py        # 새 알림 채널
└── GUI/notification_manager.py  # 여기에 등록
```

### 구현 단계

#### Step 1: 알림 채널 생성

```python
# new_notifier.py
"""
새 알림 채널 (예: Discord, Slack)
"""

import requests

class NewNotifier:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.webhook_url = ''
        self.enabled = False
        self._initialized = True
    
    def send_message(self, text: str) -> bool:
        """메시지 전송"""
        if not self.enabled or not self.webhook_url:
            return False
        
        try:
            response = requests.post(self.webhook_url, json={'content': text})
            return response.status_code == 200
        except Exception as e:
            return False
    
    def notify_trade(self, side: str, symbol: str, price: float, pnl: float = None):
        """거래 알림"""
        if pnl is not None:
            msg = f"{'🟢' if pnl > 0 else '🔴'} {side} {symbol} @ ${price:.2f} | PnL: {pnl:+.2f}%"
        else:
            msg = f"{'🚀' if side == 'Long' else '📉'} {side} {symbol} @ ${price:.2f}"
        self.send_message(msg)
```

#### Step 2: NotificationManager에 등록

```python
# GUI/notification_manager.py

from new_notifier import NewNotifier

class NotificationManager:
    def __init__(self):
        self.telegram = TelegramNotifier()
        self.new_channel = NewNotifier()  # 추가
    
    def notify_all(self, message: str):
        """모든 채널로 알림"""
        self.telegram.send_message(message)
        self.new_channel.send_message(message)
```

---

## 6️⃣ 새 지표 추가

### 파일 위치

```
utils/indicators.py  # 모든 지표는 여기에 추가
```

### 구현 단계

```python
# utils/indicators.py

def calculate_new_indicator(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    새로운 기술적 지표 계산
    
    Args:
        df: OHLCV 데이터프레임
        period: 기간
    
    Returns:
        pd.Series: 지표 값
    """
    # 계산 로직
    result = df['close'].rolling(window=period).mean()  # 예시
    return result


# 사용 예시 (core/strategy_core.py)
from utils.indicators import calculate_new_indicator

class AlphaX7Core:
    def _calculate_indicators(self, df):
        df['new_ind'] = calculate_new_indicator(df, self.params.new_period)
```

---

## 📝 체크리스트

### 새 기능 추가 시 확인사항

- [ ] 파일 생성 및 클래스 구현
- [ ] 관련 모듈에 import 추가
- [ ] 매니저/로더에 등록
- [ ] GUI 위젯 연동 (데스크톱)
- [ ] 웹 UI 연동 (필요시)
- [ ] 테스트 코드 작성
- [ ] 문서 업데이트

---

## 📚 관련 문서

- [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) - 프로젝트 구조
- [FEATURE_TREE.md](./FEATURE_TREE.md) - 기능 연동 트리
- [user_guide.py](../user_guide.py) - 사용자 가이드

---

*작성일: 2026-01-13*
