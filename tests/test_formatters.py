"""
utils/formatters 모듈 테스트
"""

import pytest  # type: ignore
from datetime import datetime, timedelta


class TestNumberFormatters:
    """숫자 포맷터 테스트"""
    
    def test_format_number(self):
        from utils.formatters import format_number
        
        assert format_number(1234567.89) == '1,234,567.89'
        assert format_number(1234567.89, decimals=0) == '1,234,568'
        assert format_number(1234.5, thousand_sep=False) == '1234.50'
        assert format_number(None) == '-'
        
    def test_format_currency(self):
        from utils.formatters import format_currency
        
        assert format_currency(1234.56) == '$1,234.56'
        assert format_currency(1234.56, 'USDT') == '$1,234.56'
        assert format_currency(1234, 'KRW', 0) == '₩1,234'
        assert format_currency(None) == '-'
        
    def test_format_percent(self):
        from utils.formatters import format_percent
        
        assert format_percent(0.05) == '+5.00%'
        assert format_percent(-0.12) == '-12.00%'
        assert format_percent(0) == '0.00%'
        assert format_percent(0.05, include_sign=False) == '5.00%'
        
    def test_format_pnl(self):
        from utils.formatters import format_pnl
        
        assert format_pnl(123.45) == '+$123.45'
        assert format_pnl(-50.00) == '-$50.00'
        assert format_pnl(0) == '+$0.00'
        
    def test_format_price(self):
        from utils.formatters import format_price
        
        # 자동 소수점
        assert ',' in format_price(45000)  # 큰 가격
        assert format_price(None) == '-'
        
    def test_abbreviate_number(self):
        from utils.formatters import abbreviate_number
        
        assert abbreviate_number(1234567890) == '1.23B'
        assert abbreviate_number(1234567) == '1.23M'
        assert abbreviate_number(12345) == '12.35K'
        assert abbreviate_number(123) == '123.00'
        assert abbreviate_number(-1234567) == '-1.23M'
        
    def test_format_with_sign(self):
        from utils.formatters import format_with_sign
        
        assert format_with_sign(123.45) == '+123.45'
        assert format_with_sign(-50) == '-50.00'
        assert format_with_sign(0) == '0.00'


class TestDateTimeFormatters:
    """날짜/시간 포맷터 테스트"""
    
    def test_format_datetime(self):
        from utils.formatters import format_datetime
        
        dt = datetime(2026, 1, 13, 10, 30, 45)
        assert format_datetime(dt) == '2026-01-13 10:30:45'
        assert format_datetime(dt, '%Y-%m-%d') == '2026-01-13'
        assert format_datetime(None) == '-'
        
    def test_format_date(self):
        from utils.formatters import format_date
        
        dt = datetime(2026, 1, 13)
        assert format_date(dt) == '2026-01-13'
        
    def test_format_time(self):
        from utils.formatters import format_time
        
        dt = datetime(2026, 1, 13, 10, 30, 45)
        assert format_time(dt) == '10:30:45'
        
    def test_format_duration(self):
        from utils.formatters import format_duration
        
        assert format_duration(45) == '45s'
        assert format_duration(65) == '1m 5s'
        assert format_duration(3661) == '1h 1m 1s'
        assert format_duration(86400) == '1d 0h 0m'
        assert format_duration(None) == '-'
        
    def test_format_relative_time(self):
        from utils.formatters import format_relative_time
        
        now = datetime.now()
        
        # 과거
        assert '분 전' in format_relative_time(now - timedelta(minutes=5))
        assert '시간 전' in format_relative_time(now - timedelta(hours=2))
        assert '일 전' in format_relative_time(now - timedelta(days=3))
        
        # 미래
        assert '분 후' in format_relative_time(now + timedelta(minutes=5))
        
    def test_format_timestamp(self):
        from utils.formatters import format_timestamp
        
        # 초 단위
        ts = datetime(2026, 1, 13, 10, 30, 0).timestamp()
        result = format_timestamp(ts)
        assert '2026-01-13' in result
        
        # 밀리초 단위
        ts_ms = ts * 1000
        result = format_timestamp(ts_ms, ms=True)
        assert '2026-01-13' in result


class TestEdgeCases:
    """엣지 케이스 테스트"""
    
    def test_none_handling(self):
        from utils.formatters import (
            format_number, format_currency, format_percent,
            format_pnl, format_datetime, format_duration
        )
        
        assert format_number(None) == '-'
        assert format_currency(None) == '-'
        assert format_percent(None) == '-'
        assert format_pnl(None) == '-'
        assert format_datetime(None) == '-'
        assert format_duration(None) == '-'
        
    def test_invalid_input(self):
        from utils.formatters import format_number, format_datetime
        
        assert format_number('invalid') == '-'  # type: ignore[arg-type]
        assert format_datetime('invalid') == '-'  # type: ignore[arg-type]
        
    def test_negative_values(self):
        from utils.formatters import format_number, format_pnl, abbreviate_number
        
        assert '-' in format_number(-1234.56)
        assert '-' in format_pnl(-100)
        assert '-' in abbreviate_number(-1000000)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
