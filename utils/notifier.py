"""
utils/notifier.py
사용자 알림 유틸리티 (텔레그램/GUI)

- telegram_notifier.py의 wrapper
- unified_bot.py에서 import 에러 해결
"""

import logging
from typing import Optional

# 텔레그램 알림 모듈 (루트 디렉토리)
try:
    from telegram_notifier import TelegramNotifier
    TELEGRAM_AVAILABLE = True
    _notifier = TelegramNotifier()  # 싱글톤 인스턴스
except ImportError:
    TELEGRAM_AVAILABLE = False
    _notifier = None
    logging.warning("[Notifier] telegram_notifier 모듈을 찾을 수 없습니다.")

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


def notify_user(
    level: str = 'info',
    title: str = '',
    message: str = '',
    exchange: str = '',
    symbol: str = '',
    **kwargs
) -> bool:
    """
    사용자 알림 전송 (텔레그램/GUI)

    Args:
        level: 알림 레벨 ('info', 'warning', 'error', 'success')
        title: 알림 제목
        message: 알림 내용
        exchange: 거래소명 (선택)
        symbol: 심볼 (선택)
        **kwargs: 추가 파라미터

    Returns:
        bool: 전송 성공 여부
    """
    # 텔레그램 알림 시도
    if TELEGRAM_AVAILABLE and _notifier and _notifier.enabled:
        try:
            # 레벨별 이모지
            emoji_map = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'success': '✅'
            }
            emoji = emoji_map.get(level, 'ℹ️')

            # 메시지 포맷팅
            full_message = f"{emoji} **{title}**\n\n{message}"

            if exchange:
                full_message += f"\n\n🏦 거래소: {exchange}"
            if symbol:
                full_message += f"\n💎 심볼: {symbol}"

            # 전송 (비동기)
            _notifier.send_message(full_message, sync=False)
            logger.debug(f"[Notifier] 텔레그램 알림 전송: {title}")
            return True

        except Exception as e:
            logger.error(f"[Notifier] 텔레그램 알림 에러: {e}")

    # 폴백: 콘솔 로그
    log_func = {
        'info': logger.info,
        'warning': logger.warning,
        'error': logger.error,
        'success': logger.info
    }.get(level, logger.info)

    log_func(f"[Notifier] {title} - {message}")
    return False


def notify_trade(
    action: str,
    symbol: str,
    side: str,
    price: float,
    size: float,
    pnl: Optional[float] = None,
    exchange: str = ''
) -> bool:
    """
    거래 알림 전송

    Args:
        action: 거래 액션 ('entry', 'exit', 'stop_loss', 'trailing')
        symbol: 심볼
        side: 방향 ('Long', 'Short')
        price: 가격
        size: 수량
        pnl: 수익률 (exit 시)
        exchange: 거래소명

    Returns:
        bool: 전송 성공 여부
    """
    action_emoji = {
        'entry': '🚀',
        'exit': '💰',
        'stop_loss': '🛑',
        'trailing': '📈'
    }

    emoji = action_emoji.get(action, '📊')
    title = f"{emoji} {action.upper()}: {symbol}"

    message = f"방향: {side}\n가격: ${price:,.2f}\n수량: {size}"

    if pnl is not None:
        pnl_emoji = '📈' if pnl > 0 else '📉'
        message += f"\n\n{pnl_emoji} 수익률: {pnl:+.2f}%"

    level = 'success' if pnl and pnl > 0 else 'info'

    return notify_user(
        level=level,
        title=title,
        message=message,
        exchange=exchange,
        symbol=symbol
    )


def notify_error(
    title: str,
    error: Exception,
    exchange: str = '',
    symbol: str = ''
) -> bool:
    """
    에러 알림 전송

    Args:
        title: 에러 제목
        error: 예외 객체
        exchange: 거래소명
        symbol: 심볼

    Returns:
        bool: 전송 성공 여부
    """
    message = f"에러 유형: {type(error).__name__}\n내용: {str(error)}"

    return notify_user(
        level='error',
        title=title,
        message=message,
        exchange=exchange,
        symbol=symbol
    )


# 하위 호환성 (기존 코드 지원)
def send_telegram_message(message: str) -> bool:
    """하위 호환성: TelegramNotifier.send_message() wrapper"""
    if TELEGRAM_AVAILABLE and _notifier:
        _notifier.send_message(message, sync=False)
        return True
    return False


def is_telegram_enabled() -> bool:
    """하위 호환성: TelegramNotifier.enabled 체크"""
    return TELEGRAM_AVAILABLE and _notifier is not None and _notifier.enabled


__all__ = [
    'notify_user',
    'notify_trade',
    'notify_error',
    'TELEGRAM_AVAILABLE',
    'is_telegram_enabled',
    'send_telegram_message',
    'TelegramNotifier'
]
