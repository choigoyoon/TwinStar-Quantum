"""
자본 관리 및 포지션 사이징 시스템
- 레버리지 설정
- 자금 설정
- 자동 포지션 사이징 (ATR 기반)
"""

import json
import os
from dataclasses import dataclass, asdict

# Logging
import logging
logger = logging.getLogger(__name__)


@dataclass
class CapitalConfig:
    """자본 관리 설정"""
    # 기본 설정
    total_capital: float = 1000.0       # 총 자본 (USD 또는 KRW)
    risk_per_trade: float = 2.0         # 포지션당 리스크 (%)
    max_positions: int = 3               # 최대 동시 포지션 수
    
    # 레버리지 설정
    leverage: int = 3                    # 기본 레버리지
    max_leverage: int = 10               # 최대 레버리지
    auto_leverage: bool = False          # 자동 레버리지 조정
    
    # 자동 포지션 사이징
    auto_sizing: bool = False            # 자동 사이징 활성화
    volatility_adjust: bool = True       # 변동성 기반 조정
    kelly_fraction: float = 0.5          # 켈리 공식 비율 (0.5 = 하프켈리)
    compounding: bool = False            # 복리 적용 (현재 잔고 기반)
    
    # 안전 설정
    max_drawdown: float = 20.0           # 최대 허용 손실 (%)
    daily_loss_limit: float = 5.0        # 일일 손실 한도 (%)
    stop_on_loss: bool = True            # 한도 도달 시 정지


# 설정 파일 경로
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'data', 'capital_config.json')


def load_capital_config() -> CapitalConfig:
    """자본 설정 로드"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return CapitalConfig(**data)
        except Exception as e:
            logger.info(f"설정 로드 오류: {e}")
    return CapitalConfig()


def save_capital_config(config: CapitalConfig):
    """자본 설정 저장"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(asdict(config), f, indent=2, ensure_ascii=False)


class PositionSizer:
    """포지션 사이징 계산기"""
    
    def __init__(self, config: CapitalConfig = None):
        self.config = config or load_capital_config()
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        atr: float = None,
        win_rate: float = 0.75
    ) -> dict:
        """
        포지션 크기 계산
        
        Args:
            entry_price: 진입가
            stop_loss: 손절가
            atr: ATR (자동 사이징용)
            win_rate: 승률 (켈리 공식용)
        
        Returns:
            {
                'position_size': 포지션 크기 (USD),
                'quantity': 수량,
                'leverage': 레버리지,
                'risk_amount': 리스크 금액,
                'risk_percent': 리스크 비율
            }
        """
        # 리스크 금액 계산
        risk_percent = self.config.risk_per_trade
        
        # 자동 사이징: 변동성 조정
        if self.config.auto_sizing and atr:
            risk_percent = self._adjust_for_volatility(risk_percent, atr, entry_price)
        
        # 자동 사이징: 켈리 공식
        if self.config.auto_sizing and win_rate:
            kelly_size = self._kelly_criterion(win_rate)
            risk_percent = min(risk_percent, kelly_size)
        
        risk_amount = self.config.total_capital * (risk_percent / 100)
        
        # 손절 거리 (%)
        sl_distance = abs(entry_price - stop_loss) / entry_price
        
        # 포지션 크기 계산
        if sl_distance > 0:
            position_size = risk_amount / sl_distance
        else:
            position_size = risk_amount * 10  # 기본값
        
        # 레버리지 조정
        leverage = self.config.leverage
        if self.config.auto_leverage:
            leverage = self._auto_leverage(sl_distance)
        
        # 수량 계산
        quantity = position_size / entry_price
        
        return {
            'position_size': round(position_size, 2),
            'quantity': round(quantity, 6),
            'leverage': leverage,
            'risk_amount': round(risk_amount, 2),
            'risk_percent': round(risk_percent, 2)
        }
    
    def _adjust_for_volatility(
        self,
        base_risk: float,
        atr: float,
        price: float
    ) -> float:
        """변동성 기반 리스크 조정"""
        # ATR % 계산
        atr_percent = (atr / price) * 100
        
        # 기준: ATR 1% = 정상
        # ATR 높으면 리스크 축소, 낮으면 확대
        if atr_percent > 2.0:
            # 고변동성: 리스크 50% 축소
            return base_risk * 0.5
        elif atr_percent > 1.5:
            # 중변동성: 리스크 25% 축소
            return base_risk * 0.75
        elif atr_percent < 0.5:
            # 저변동성: 리스크 25% 확대
            return min(base_risk * 1.25, 5.0)
        
        return base_risk
    
    def _kelly_criterion(self, win_rate: float, risk_reward: float = 2.0) -> float:
        """
        켈리 공식으로 최적 베팅 비율 계산
        
        Kelly = W - (1-W)/R
        W = 승률
        R = 리스크/리워드 비율
        """
        kelly = win_rate - (1 - win_rate) / risk_reward
        
        # 하프 켈리 적용 (보수적)
        kelly *= self.config.kelly_fraction
        
        # 범위 제한 (0.5% ~ 5%)
        return max(0.5, min(kelly * 100, 5.0))
    
    def _auto_leverage(self, sl_distance: float) -> int:
        """손절 거리 기반 자동 레버리지"""
        # 손절이 멀면 레버리지 낮게, 가까우면 높게
        if sl_distance > 0.05:      # 5% 이상
            return min(2, self.config.max_leverage)
        elif sl_distance > 0.03:    # 3~5%
            return min(3, self.config.max_leverage)
        elif sl_distance > 0.02:    # 2~3%
            return min(5, self.config.max_leverage)
        elif sl_distance > 0.01:    # 1~2%
            return min(7, self.config.max_leverage)
        else:                        # 1% 미만
            return min(10, self.config.max_leverage)


# 싱글톤
_config = None
_sizer = None

def get_capital_config() -> CapitalConfig:
    global _config
    if _config is None:
        _config = load_capital_config()
    return _config

def get_position_sizer() -> PositionSizer:
    global _sizer
    if _sizer is None:
        _sizer = PositionSizer()
    return _sizer


# 테스트
if __name__ == "__main__":
    config = CapitalConfig(
        total_capital=10000,
        risk_per_trade=2.0,
        leverage=5,
        auto_sizing=True
    )
    
    sizer = PositionSizer(config)
    
    # 예시: BTC $100,000, SL $98,000
    result = sizer.calculate_position_size(
        entry_price=100000,
        stop_loss=98000,
        atr=1500,
        win_rate=0.75
    )
    
    logger.info("=== 포지션 사이징 결과 ===")
    for k, v in result.items():
        logger.info(f"  {k}: {v}")
