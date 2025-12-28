import os
import sys
import shutil
import pandas as pd
import logging
from pathlib import Path
from typing import List

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# 기존 모듈 임포트
from GUI.data_manager import DataManager
from GUI.symbol_cache import SymbolCache
from utils.symbol_converter import extract_base, convert_symbol

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def get_upbit_symbols() -> List[str]:
    """업비트 원화 마켓 심볼 목록 반환"""
    sc = SymbolCache()
    raw_exchanges = sc._cache.get('exchanges', {})
    if 'upbit' not in raw_exchanges:
        logging.error("Upbit not found in SymbolCache")
        return []
        
    raw_symbols = raw_exchanges['upbit'].get('symbols', [])
    res = []
    for s in raw_symbols:
        symbol_name = (s.get('symbol') or '').upper()
        quote = (s.get('quote') or '').upper()
        if quote == 'KRW' or '/KRW' in symbol_name or '-KRW' in symbol_name:
            base = s.get('base') or extract_base(s.get('id', ''))
            res.append(base.upper())
            
    logging.info(f"Upbit filtered bases (KRW): {len(res)} symbols")
    return list(set(res))

def get_bithumb_symbols() -> List[str]:
    """빗썸 원화 마켓 심볼 목록 반환"""
    sc = SymbolCache()
    raw_exchanges = sc._cache.get('exchanges', {})
    if 'bithumb' not in raw_exchanges:
        logging.error("Bithumb not found in SymbolCache")
        return []
        
    raw_symbols = raw_exchanges['bithumb'].get('symbols', [])
    res = []
    for s in raw_symbols:
        symbol_name = (s.get('symbol') or '').upper()
        quote = (s.get('quote') or '').upper()
        if quote == 'KRW' or '/KRW' in symbol_name or '_KRW' in symbol_name:
            base = s.get('base') or extract_base(s.get('id', ''))
            res.append(base.upper())

    logging.info(f"Bithumb filtered bases (KRW): {len(res)} symbols")
    return list(set(res))

def get_filtered_symbols(exchange_name: str) -> List[str]:
    """
    거래소별 심볼 목록 반환
    - upbit: 전체
    - bithumb: 업비트 교집합만
    - 기타: 자체 목록
    """
    exchange_name = exchange_name.lower()
    
    if exchange_name == 'upbit':
        return get_upbit_symbols()
    
    elif exchange_name == 'bithumb':
        upbit_bases = set(get_upbit_symbols())
        bithumb_bases = set(get_bithumb_symbols())
        # 교집합 추출
        common = sorted(list(upbit_bases & bithumb_bases))
        logging.info(f"🔍 [HYBRID] 업비트 {len(upbit_bases)}개, 빗썸 {len(bithumb_bases)}개 → 교집합 {len(common)}개")
        return common
    
    else:
        sc = SymbolCache()
        # 기본적으로 선물(swap) 데이터 수집
        symbols = sc.get_symbols(exchange_name, 'swap')
        return [extract_base(s) for s in symbols]

def fetch_from_upbit(symbol: str, timeframe: str):
    """업비트에서 특정 심볼의 데이터를 가져옴"""
    dm = DataManager()
    df = dm.download(
        symbol=symbol,
        exchange='upbit',
        timeframe=timeframe,
        limit=500000
    )
    return df

def download_symbol(exchange_name: str, symbol: str, timeframe: str) -> int:
    """
    심볼 데이터 수집
    - bithumb: 업비트에서 수집 → 양쪽 파일 저장
    - 기타: 자체 수집
    """
    dm = DataManager()
    exchange_name = exchange_name.lower()
    
    if exchange_name == 'bithumb':
        logging.info(f"🔄 [HYBRID] Downloading {symbol} from Upbit for Bithumb...")
        # BTC -> BTC/KRW 형식으로 변환 시도 (DataManager가 내부적으로 처리하길 기대)
        # 만약 SymbolConverter가 필요하다면 여기서 사용
        df = dm.download(symbol=symbol, exchange='upbit', timeframe=timeframe, limit=500000)
        
        if df is None or df.empty:
            logging.error(f"❌ [HYBRID] {symbol} 데이터 수집 실패")
            return 0
        
        # 업비트 파일 경로 확인
        upbit_path = dm._get_cache_path('upbit', symbol, timeframe)
        bithumb_path = dm._get_cache_path('bithumb', symbol, timeframe)
        
        try:
            shutil.copy(upbit_path, bithumb_path)
            logging.info(f"✅ [HYBRID] Copy: {upbit_path.name} -> {bithumb_path.name}")
        except Exception as e:
            logging.error(f"❌ [HYBRID] Copy failed: {e}")
            
        return len(df)
    
    else:
        df = dm.download(symbol=symbol, exchange=exchange_name, timeframe=timeframe, limit=500000)
        return len(df) if df is not None else 0

def download_all(exchange_name: str, timeframe: str):
    """특정 거래소의 모든 (필터링된) 심볼 다운로드"""
    symbols = get_filtered_symbols(exchange_name)
    total = len(symbols)
    
    logging.info(f"🚀 [START] '{exchange_name}' {total}개 심볼 수집 시작 (TF: {timeframe})")
    
    success = 0
    for i, symbol in enumerate(symbols):
        logging.info(f"[{i+1}/{total}] Processing {symbol}...")
        count = download_symbol(exchange_name, symbol, timeframe)
        if count > 0:
            success += 1
            
    logging.info(f"🏁 [FINISHED] {exchange_name} 수집 완료: {success}/{total} 성공")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ex = sys.argv[1]
        tf = sys.argv[2] if len(sys.argv) > 2 else '1h'
        download_all(ex, tf)
    else:
        print("Usage: py utils/data_downloader.py [exchange] [timeframe]")
        print("Example: py utils/data_downloader.py bithumb 1h")
