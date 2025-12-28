"""
거래 안전 관리 시스템
- 일일 손실 한도
- 최대 손실 한도 (MDD)
- 자동 중지 기능
"""

import os
import sys
import json
from datetime import datetime, date
from typing import Optional
from dataclasses import dataclass, asdict


# [FIX] EXE 호환 경로 처리
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)

# 설정 파일
SAFETY_CONFIG_FILE = os.path.join(BASE_DIR, 'data', 'safety_config.json')
DAILY_PNL_FILE = os.path.join(BASE_DIR, 'data', 'daily_pnl.json')


@dataclass
class SafetyConfig:
    """안전 설정"""
    daily_loss_limit: float = 100.0     # 일일 손실 한도 (USD)
    max_drawdown: float = 500.0         # 최대 손실 한도 (USD)
    auto_stop_on_limit: bool = True     # 한도 도달 시 자동 중지
    notify_on_warning: bool = True      # 경고 시 알림
    warning_threshold: float = 0.7      # 경고 기준 (70%)


@dataclass
class DailyPnL:
    """일일 손익"""
    date: str = ""
    total_pnl: float = 0.0
    trades: int = 0
    wins: int = 0
    losses: int = 0
    is_stopped: bool = False


def load_safety_config() -> SafetyConfig:
    """안전 설정 로드"""
    if os.path.exists(SAFETY_CONFIG_FILE):
        try:
            with open(SAFETY_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return SafetyConfig(**data)
        except:
            pass
    return SafetyConfig()


def save_safety_config(config: SafetyConfig):
    """안전 설정 저장"""
    os.makedirs(os.path.dirname(SAFETY_CONFIG_FILE), exist_ok=True)
    with open(SAFETY_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(asdict(config), f, indent=2)


def load_daily_pnl() -> DailyPnL:
    """오늘 손익 로드"""
    today = date.today().isoformat()
    
    if os.path.exists(DAILY_PNL_FILE):
        try:
            with open(DAILY_PNL_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 오늘 날짜인지 확인
                if data.get('date') == today:
                    return DailyPnL(**data)
        except:
            pass
    
    # 새 날짜면 리셋
    return DailyPnL(date=today)


def save_daily_pnl(pnl: DailyPnL):
    """오늘 손익 저장"""
    os.makedirs(os.path.dirname(DAILY_PNL_FILE), exist_ok=True)
    with open(DAILY_PNL_FILE, 'w', encoding='utf-8') as f:
        json.dump(asdict(pnl), f, indent=2)


class TradingSafetyManager:
    """거래 안전 관리자"""
    
    def __init__(self):
        self.config = load_safety_config()
        self.daily_pnl = load_daily_pnl()
    
    def record_trade(self, pnl: float, is_win: bool) -> dict:
        """
        거래 기록 및 안전 체크
        
        Returns:
            {
                'allowed': bool,  # 계속 거래 가능 여부
                'warning': str,   # 경고 메시지 (있으면)
                'stopped': bool,  # 자동 중지 여부
            }
        """
        # 오늘 날짜 확인 (날짜 변경 시 리셋)
        today = date.today().isoformat()
        if self.daily_pnl.date != today:
            self.daily_pnl = DailyPnL(date=today)
        
        # 손익 기록
        self.daily_pnl.total_pnl += pnl
        self.daily_pnl.trades += 1
        if is_win:
            self.daily_pnl.wins += 1
        else:
            self.daily_pnl.losses += 1
        
        save_daily_pnl(self.daily_pnl)
        
        # 안전 체크
        result = {
            'allowed': True,
            'warning': None,
            'stopped': False
        }
        
        # 일일 손실 체크
        if self.daily_pnl.total_pnl < 0:
            loss = abs(self.daily_pnl.total_pnl)
            limit = self.config.daily_loss_limit
            
            # 경고 기준 도달
            if loss >= limit * self.config.warning_threshold:
                result['warning'] = f"Daily loss warning: ${loss:.2f} / ${limit:.2f}"
            
            # 한도 도달
            if loss >= limit:
                result['warning'] = f"DAILY LOSS LIMIT REACHED: ${loss:.2f}"
                
                if self.config.auto_stop_on_limit:
                    result['allowed'] = False
                    result['stopped'] = True
                    self.daily_pnl.is_stopped = True
                    save_daily_pnl(self.daily_pnl)
        
        return result
    
    def check_can_trade(self) -> dict:
        """거래 가능 여부 확인"""
        today = date.today().isoformat()
        
        # 날짜 변경 시 리셋
        if self.daily_pnl.date != today:
            self.daily_pnl = DailyPnL(date=today)
            save_daily_pnl(self.daily_pnl)
            return {'allowed': True, 'reason': 'New day'}
        
        # 이미 중지됨
        if self.daily_pnl.is_stopped:
            return {
                'allowed': False,
                'reason': f"Daily limit reached: ${abs(self.daily_pnl.total_pnl):.2f}"
            }
        
        # 한도 체크
        if self.daily_pnl.total_pnl < 0:
            loss = abs(self.daily_pnl.total_pnl)
            if loss >= self.config.daily_loss_limit:
                return {
                    'allowed': False,
                    'reason': f"Daily limit reached: ${loss:.2f}"
                }
        
        return {'allowed': True, 'reason': 'OK'}
    
    def reset_daily(self):
        """일일 기록 초기화 (수동)"""
        self.daily_pnl = DailyPnL(date=date.today().isoformat())
        save_daily_pnl(self.daily_pnl)
    
    def get_status(self) -> dict:
        """현재 상태 조회"""
        loss = abs(min(0, self.daily_pnl.total_pnl))
        limit = self.config.daily_loss_limit
        
        return {
            'date': self.daily_pnl.date,
            'trades': self.daily_pnl.trades,
            'pnl': self.daily_pnl.total_pnl,
            'loss': loss,
            'limit': limit,
            'remaining': max(0, limit - loss),
            'usage_percent': (loss / limit * 100) if limit > 0 else 0,
            'is_stopped': self.daily_pnl.is_stopped
        }


# 싱글톤
_safety_manager = None

def get_safety_manager() -> TradingSafetyManager:
    global _safety_manager
    if _safety_manager is None:
        _safety_manager = TradingSafetyManager()
    return _safety_manager


# 테스트
if __name__ == "__main__":
    manager = get_safety_manager()
    
    print("=== 안전 관리 테스트 ===\n")
    
    # 거래 기록
    trades = [(50, True), (-30, False), (-40, False), (-50, False)]
    
    for pnl, is_win in trades:
        result = manager.record_trade(pnl, is_win)
        status = manager.get_status()
        
        print(f"Trade: ${pnl:+.0f}")
        print(f"  Total PnL: ${status['pnl']:.2f}")
        print(f"  Remaining: ${status['remaining']:.2f}")
        print(f"  Usage: {status['usage_percent']:.0f}%")
        
        if result['warning']:
            print(f"  WARNING: {result['warning']}")
        if result['stopped']:
            print(f"  STOPPED!")
        print()
