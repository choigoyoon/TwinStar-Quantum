"""
utils/validators.py - 입력 검증 유틸리티
보안을 위한 사용자 입력 검증
"""
import re
import os
from typing import Tuple, Union

# Logging
import logging
logger = logging.getLogger(__name__)


# ========== 심볼 검증 ==========

SYMBOL_PATTERN = re.compile(r'^[A-Z0-9\-_]{2,20}(USDT|USD|BTC|ETH|KRW)?$', re.IGNORECASE)
VALID_EXCHANGES = {'bybit', 'binance', 'okx', 'bitget', 'bingx', 'upbit', 'bithumb'}


def validate_symbol(symbol: str) -> Tuple[bool, str]:
    """
    심볼명 검증
    
    Args:
        symbol: 심볼명 (예: 'BTCUSDT')
        
    Returns:
        (valid, message) 튜플
    """
    if not symbol:
        return False, "심볼이 비어있습니다"
    
    symbol = symbol.strip().upper()
    
    if len(symbol) < 2 or len(symbol) > 20:
        return False, "심볼 길이는 2~20자입니다"
    
    if not SYMBOL_PATTERN.match(symbol):
        return False, "유효하지 않은 심볼 형식입니다"
    
    # 위험 문자 방지
    if any(c in symbol for c in ['..', '/', '\\', '<', '>', '|', '*', '?']):
        return False, "심볼에 위험 문자가 포함되어 있습니다"
    
    return True, symbol


def validate_exchange(exchange: str) -> Tuple[bool, str]:
    """거래소명 검증"""
    if not exchange:
        return False, "거래소가 비어있습니다"
    
    exchange = exchange.strip().lower()
    
    if exchange not in VALID_EXCHANGES:
        return False, f"지원하지 않는 거래소입니다: {exchange}"
    
    return True, exchange


# ========== 숫자 검증 ==========

def validate_number(
    value,
    min_val: float | None = None,
    max_val: float | None = None,
    name: str = "value"
) -> Tuple[bool, Union[float, str]]:
    """
    숫자 범위 검증
    
    Args:
        value: 검증할 값
        min_val: 최소값 (None이면 제한 없음)
        max_val: 최대값 (None이면 제한 없음)
        name: 오류 메시지용 이름
        
    Returns:
        (valid, value_or_error) 튜플
    """
    try:
        num = float(value)
    except (TypeError, ValueError):
        return False, f"{name}은(는) 숫자여야 합니다"
    
    if min_val is not None and num < min_val:
        return False, f"{name}은(는) {min_val} 이상이어야 합니다"
    
    if max_val is not None and num > max_val:
        return False, f"{name}은(는) {max_val} 이하여야 합니다"
    
    return True, num


def validate_leverage(leverage) -> Tuple[bool, Union[int, str]]:
    """레버리지 검증 (1~125)"""
    valid, result = validate_number(leverage, 1, 125, "레버리지")
    if valid:
        return True, int(result)  # type: ignore[arg-type]
    return False, str(result)


def validate_amount(amount) -> Tuple[bool, Union[float, str]]:
    """금액 검증 (0 초과)"""
    return validate_number(amount, 0.0001, 1000000000, "금액")


def validate_percentage(value, name: str = "비율") -> Tuple[bool, Union[float, str]]:
    """퍼센트 검증 (0~100)"""
    return validate_number(value, 0, 100, name)


# ========== 경로 검증 ==========

def validate_path(path: str, base_dir: str | None = None) -> Tuple[bool, str]:
    """
    파일 경로 검증 (path traversal 방지)
    
    Args:
        path: 검증할 경로
        base_dir: 허용된 기본 디렉토리 (None이면 현재 디렉토리)
        
    Returns:
        (valid, resolved_path_or_error) 튜플
    """
    if not path:
        return False, "경로가 비어있습니다"
    
    # 위험 패턴 검사
    dangerous_patterns = ['..', '~', '$', '%', '`', '|', ';', '&']
    for pattern in dangerous_patterns:
        if pattern in path:
            return False, f"경로에 위험 패턴이 포함되어 있습니다: {pattern}"
    
    # 절대 경로로 변환
    if base_dir:
        base_dir = os.path.abspath(base_dir)
        full_path = os.path.abspath(os.path.join(base_dir, path))
        
        # base_dir 외부 접근 방지
        if not full_path.startswith(base_dir):
            return False, "허용된 디렉토리 외부 접근 시도"
    else:
        full_path = os.path.abspath(path)
    
    return True, full_path


def validate_filename(filename: str) -> Tuple[bool, str]:
    """파일명 검증 (특수문자 제한)"""
    if not filename:
        return False, "파일명이 비어있습니다"
    
    # 허용된 문자만
    if not re.match(r'^[\w\-\.]+$', filename):
        return False, "파일명에 허용되지 않은 문자가 있습니다"
    
    # 위험 확장자 체크
    dangerous_ext = ['.exe', '.bat', '.cmd', '.sh', '.ps1']
    for ext in dangerous_ext:
        if filename.lower().endswith(ext):
            return False, f"위험한 파일 확장자입니다: {ext}"
    
    return True, filename


# ========== API 키 검증 ==========

def validate_api_key(key: str) -> Tuple[bool, str]:
    """API 키 기본 형식 검증"""
    if not key:
        return False, "API 키가 비어있습니다"
    
    key = key.strip()
    
    if len(key) < 16:
        return False, "API 키가 너무 짧습니다"
    
    if len(key) > 256:
        return False, "API 키가 너무 깁니다"
    
    # 기본 문자만 허용
    if not re.match(r'^[A-Za-z0-9\-_]+$', key):
        return False, "API 키 형식이 올바르지 않습니다"
    
    return True, key


# ========== 통합 검증 ==========

class InputValidator:
    """통합 입력 검증기"""
    
    @staticmethod
    def validate_trade_params(params: dict) -> Tuple[bool, dict]:
        """
        거래 파라미터 전체 검증
        
        Returns:
            (valid, validated_params_or_errors)
        """
        errors = []
        validated = {}
        
        # 심볼
        if 'symbol' in params:
            valid, result = validate_symbol(params['symbol'])
            if valid:
                validated['symbol'] = result
            else:
                errors.append(result)
        
        # 레버리지
        if 'leverage' in params:
            valid, result = validate_leverage(params['leverage'])
            if valid:
                validated['leverage'] = result
            else:
                errors.append(result)
        
        # 금액
        if 'amount' in params:
            valid, result = validate_amount(params['amount'])
            if valid:
                validated['amount'] = result
            else:
                errors.append(result)
        
        if errors:
            return False, {'errors': errors}
        
        return True, validated


if __name__ == '__main__':
    # 테스트
    logger.info("=== Symbol Validation ===")
    logger.info(f"{validate_symbol('BTCUSDT')}")  # (True, 'BTCUSDT')
    logger.info(f"{validate_symbol('BTC../USDT')}")  # (False, '...')
    
    logger.info("\n=== Number Validation ===")
    logger.info(f"{validate_leverage(10)}")  # (True, 10)
    logger.info(f"{validate_leverage(200)}")  # (False, '...')
    
    logger.info("\n=== Path Validation ===")
    logger.info(f"{validate_path('data/test.txt', '/app')}")  # (True, '/app/data/test.txt')
    logger.info(f"{validate_path('../../../etc/passwd', '/app')}")  # (False, '...')
