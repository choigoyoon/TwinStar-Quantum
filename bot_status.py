"""
봇 상태 모니터링 시스템
- 실시간 봇 상태 확인
- 포지션 정보 조회
- 상태 파일 기반 통신
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass, asdict


# 상태 파일 경로
BOT_STATUS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'bot_status.json')


@dataclass
class BotStatus:
    """봇 상태"""
    running: bool = False
    exchange: str = ""
    symbol: str = ""
    strategy: str = ""
    state: str = "stopped"  # stopped, waiting, detecting, position_open
    last_update: str = ""
    
    # 포지션 정보 (있으면)
    position_side: str = ""  # Long/Short
    entry_price: float = 0.0
    current_price: float = 0.0
    stop_loss: float = 0.0
    size: float = 0.0
    pnl_percent: float = 0.0
    pnl_usd: float = 0.0
    
    # 통계
    today_trades: int = 0
    today_pnl: float = 0.0
    total_trades: int = 0
    win_rate: float = 0.0


def save_bot_status(status: BotStatus):
    """봇 상태 저장"""
    os.makedirs(os.path.dirname(BOT_STATUS_FILE), exist_ok=True)
    status.last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(BOT_STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(asdict(status), f, indent=2, ensure_ascii=False)


def load_bot_status() -> BotStatus:
    """봇 상태 로드"""
    if os.path.exists(BOT_STATUS_FILE):
        try:
            with open(BOT_STATUS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return BotStatus(**data)
        except:
            pass
    return BotStatus()


def get_bot_state_text(status: BotStatus) -> tuple:
    """상태 텍스트 및 색상 반환"""
    if not status.running:
        return "정지됨", "#787b86"
    
    state_map = {
        "waiting": ("신호 대기 중", "#2962FF"),
        "detecting": ("패턴 감지 중", "#ff9800"),
        "position_open": ("포지션 보유", "#26a69a"),
        "error": ("오류 발생", "#ef5350"),
    }
    
    return state_map.get(status.state, ("실행 중", "#26a69a"))





# 봇에서 호출할 함수들
def update_bot_running(exchange: str, symbol: str, strategy: str):
    """봇 시작 시 호출"""
    status = load_bot_status()
    status.running = True
    status.exchange = exchange
    status.symbol = symbol
    status.strategy = strategy
    status.state = "waiting"
    save_bot_status(status)


def update_bot_state(state: str):
    """상태 변경 시 호출"""
    status = load_bot_status()
    status.state = state
    save_bot_status(status)


def update_position(side: str, entry: float, current: float, 
                   sl: float, size: float, pnl_pct: float, pnl_usd: float):
    """포지션 업데이트"""
    status = load_bot_status()
    status.state = "position_open"
    status.position_side = side
    status.entry_price = entry
    status.current_price = current
    status.stop_loss = sl
    status.size = size
    status.pnl_percent = pnl_pct
    status.pnl_usd = pnl_usd
    save_bot_status(status)


def clear_position():
    """포지션 청산 시 호출"""
    status = load_bot_status()
    status.state = "waiting"
    status.position_side = ""
    status.entry_price = 0
    status.current_price = 0
    status.stop_loss = 0
    status.size = 0
    status.pnl_percent = 0
    status.pnl_usd = 0
    save_bot_status(status)


def update_bot_stopped():
    """봇 중지 시 호출"""
    status = load_bot_status()
    status.running = False
    status.state = "stopped"
    save_bot_status(status)


# 테스트
if __name__ == "__main__":
    # 시작
    update_bot_running("Bybit", "BTCUSDT", "Alpha-X7 Plus")
    print("봇 시작 상태:", load_bot_status())
    
    # 포지션 오픈
    update_position("Long", 98000, 99500, 96500, 0.05, 1.53, 75.0)
    status = load_bot_status()
    print("\n포지션 정보:")
    print(f"  {status.position_side} @ {status.entry_price}")
    print(f"  PnL: {status.pnl_percent:.2f}% (${status.pnl_usd:.2f})")
    
    # 상태 텍스트
    text, color = get_bot_state_text(status)
    print(f"\n상태: {text} ({color})")

