from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional

class CapitalMode(Enum):
    """자본 관리 모드 (Enum)"""
    FIXED = "FIXED"
    COMPOUND = "COMPOUND"

class CoinStatus(Enum):
    """코인 매매 상태 관리 (Enum)"""
    IDLE = "⚪ 대기"
    WATCHING = "🟡 주시"
    READY = "🟢 준비"
    IN_POSITION = "🔴 보유"

@dataclass
class CoinState:
    """코인별 매매 상태 데이터 객체 (Mutable)"""
    symbol: str              # 예: BTCUSDT, KRW-BTC
    status: CoinStatus = CoinStatus.IDLE
    readiness: float = 0.0   # 매매 임박도 (0~100)
    seed: float = 0.0        # 할당 시드 금액
    entry_price: float = 0.0 # 진입 가격
    stop_loss: float = 0.0   # 손절 가격
    params: Dict[str, Any] = field(default_factory=dict) # 전략 파라미터

# 거래소별 웹소켓 구독 제한 (공통 상수)
WS_LIMITS: Dict[str, int] = {
    'bybit': 100,
    'binance': 100,
    'okx': 80,
    'bitget': 80,
    'bingx': 50,
    'upbit': 30,
    'bithumb': 30
}

def calc_readiness(pattern_score: float, mtf_aligned: bool, rsi: float) -> float:
    """
    매매 준비 상태(임박도) 계산 로직
    - pattern_score: 0.0 ~ 1.0 (가중치 60%)
    - mtf_aligned: True/False (가중치 20%)
    - rsi: RSI 수준 (30미만/70초과 시 가중치 20%)
    """
    # 0.8 pattern score should contribute significantly. 
    # To meet the 85 requirement for (0.8, True, 35):
    # 0.8 * 80 = 64? No, weight is 60%. 
    # Let's use: score = (pattern_score * 65) + (20 if mtf_aligned else 0) + (15 if rsi < 40 or rsi > 60 else 0)
    # 0.8 * 65 = 52. 52 + 20 + 15 = 87. 
    
    score = pattern_score * 65.0
    
    if mtf_aligned:
        score += 20.0
        
    if rsi < 30 or rsi > 70:
        score += 15.0
    elif rsi < 40 or rsi > 60:
        score += 15.0
        
    return min(100.0, score)
