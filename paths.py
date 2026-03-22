"""
paths.py - 런타임 파일 경로 중앙 관리
모든 파일 경로는 이 모듈을 통해 관리됨
"""

import sys
import os
from typing import Optional
from datetime import datetime
from pathlib import Path


def get_base_path() -> str:
    """사용자 데이터 저장용 (EXE 옆)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_internal_path() -> str:
    """내부 번들 자원용 (_MEIPASS)"""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


class Paths:
    """모든 경로를 중앙 관리하는 클래스"""
    
    # ========== 기초 경로 ==========
    BASE = Path(get_base_path())
    INTERNAL_BASE = Path(get_internal_path())
    ROOT = BASE  # [Alias] 전문 검증 시스템(v2.2) 호환성용
    
    # ========== 고정 경로 ==========
    # 배포 시 EXE 내부에 포함되는 자원은 INTERNAL_BASE 사용
    CONFIG = INTERNAL_BASE / 'config'                        # 번들된 설정 예시
    USER_CONFIG = BASE / 'config'                            # 사용자 수정가능 설정 (EXE 옆)
    USER = BASE / 'user'                                     # 사용자 데이터 루트
    LOGS = BASE / 'logs'                                     # 로그 폴더
    DATA = BASE / 'data'                                     # 데이터 폴더
    USER_DATA = USER                                         # [Alias] 호환성용
    CACHE = DATA / 'cache'                                   # 캐시
    PRESETS = USER_CONFIG / 'presets'                        # 프리셋 폴더
    
    # ========== 전역 경로 ==========
    GLOBAL = USER / 'global'
    CREDENTIALS = GLOBAL / 'credentials'                     # 인증 정보
    SETTINGS = GLOBAL / 'settings'                           # 앱 설정
    BACKUP = USER / 'backup'                                 # 자동 백업
    
    # ========== 거래소/심볼별 경로 ==========
    EXCHANGES = USER / 'exchanges'
    
    # ========== 단일 파일 경로 ==========
    @classmethod
    def encrypted_keys(cls) -> str:
        """API 키 암호화 파일"""
        return str(cls.CREDENTIALS / 'encrypted_keys.dat')
    
    @classmethod
    def license_db(cls) -> str:
        """라이선스 DB"""
        return str(cls.CREDENTIALS / 'license.db')
    
    @classmethod
    def app_config(cls) -> str:
        """앱 설정 파일"""
        return str(cls.SETTINGS / 'app_config.json')
    
    @classmethod
    def telegram_config(cls) -> str:
        """텔레그램 설정 파일"""
        return str(cls.SETTINGS / 'telegram.json')
    
    @classmethod
    def payment_config(cls) -> str:
        """결제 설정 (배포 시 포함)"""
        return str(cls.CONFIG / 'payment_config.json')
    
    @classmethod
    def cumulative_stats(cls) -> str:
        """누적 통계"""
        return str(cls.GLOBAL / 'cumulative.json')
    
    # ========== 거래소/심볼별 경로 ==========
    @classmethod
    def exchange_dir(cls, exchange: str) -> str:
        """거래소 폴더 경로"""
        return str(cls.EXCHANGES / exchange.lower())
    
    @classmethod
    def symbol_dir(cls, exchange: str, symbol: str) -> str:
        """심볼 폴더 경로"""
        return str(Path(cls.exchange_dir(exchange)) / symbol.upper().replace('/', '_'))
    
    @classmethod
    def history(cls, exchange: str, symbol: str) -> str:
        """거래 기록 파일"""
        return str(Path(cls.symbol_dir(exchange, symbol)) / 'history.json')
    
    @classmethod
    def state(cls, exchange: str, symbol: str) -> str:
        """현재 상태 파일"""
        return str(Path(cls.symbol_dir(exchange, symbol)) / 'state.json')
    
    @classmethod
    def stats(cls, exchange: str, symbol: str) -> str:
        """심볼 통계 파일"""
        return str(Path(cls.symbol_dir(exchange, symbol)) / 'stats.json')
    
    # ========== 로그 경로 ==========
    @classmethod
    def daily_log(cls, date_str: Optional[str] = None) -> str:
        """일별 로그 파일"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        return str(cls.LOGS / f'{date_str}.log')
    
    @classmethod
    def error_log(cls) -> str:
        """에러 로그 파일"""
        return str(cls.LOGS / 'error.log')
    
    # ========== 캐시 경로 ==========
    @classmethod
    def backtest_data(cls, filename: str = 'btc_5m_bybit.csv') -> str:
        """백테스트 데이터"""
        return str(cls.CACHE / filename)
    
    # ========== 유틸리티 ==========
    @classmethod
    def ensure_dirs(cls, exchange: Optional[str] = None, symbol: Optional[str] = None):
        """필요한 폴더 자동 생성"""
        dirs = [
            cls.CONFIG,
            cls.LOGS,
            cls.CACHE,
            cls.CREDENTIALS,
            cls.SETTINGS,
            cls.BACKUP,
            cls.EXCHANGES,
        ]
        
        if exchange:
            dirs.append(Path(cls.exchange_dir(exchange)))
        if exchange and symbol:
            dirs.append(Path(cls.symbol_dir(exchange, symbol)))
        
        for d in dirs:
            os.makedirs(d, exist_ok=True)
    
    @classmethod
    def ensure_all(cls):
        """모든 기본 폴더 생성"""
        cls.ensure_dirs()


# 모듈 로드 시 기본 폴더 생성
# [주석 처리] 앱 시작점(staru_main.py)에서 명시적 호출
# Paths.ensure_all()
