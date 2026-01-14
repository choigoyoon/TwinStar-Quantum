
from pathlib import Path
import time

base = Path(__file__).parent

print("=" * 60)
print("전체 거래소 WS + 시간 동기화 구현 계획")
print("=" * 60)

# ============================================
# 1. 현재 상태 파악
# ============================================
print("\n[1] 현재 거래소별 구현 상태")

exchanges_dir = base / 'exchanges'
status = {}

for ex_file in sorted(exchanges_dir.glob('*_exchange.py')):
    if 'base' in ex_file.name or 'ccxt' in ex_file.name:
        continue
        
    name = ex_file.stem.replace('_exchange', '')
    code = ex_file.read_text(encoding='utf-8', errors='ignore')
    
    # Simple checks using string matching
    has_ws = 'def start_websocket' in code and 'pass' not in code[code.find('def start_websocket'):code.find('def start_websocket')+200]
    has_time = 'fetchTime' in code or 'sync_time' in code or 'time_offset' in code
    has_auto_sync = 'auto' in code.lower() and 'sync' in code.lower()
    
    status[name] = {
        'ws': has_ws,
        'time': has_time,
        'auto': has_auto_sync
    }
    
    ws_icon = '✅' if has_ws else '❌'
    time_icon = '✅' if has_time else '❌'
    auto_icon = '✅' if has_auto_sync else '❌'
    
    print(f"  {name:12} WS={ws_icon} Time={time_icon} AutoSync={auto_icon}")

# ============================================
# 2. 필요한 작업 목록
# ============================================
print("\n[2] 필요한 작업")

needs_ws = [k for k, v in status.items() if not v['ws']]
needs_time = [k for k, v in status.items() if not v['time']]

print(f"\n  WS 구현 필요: {needs_ws}")
print(f"  시간동기화 필요: {needs_time}")

# ============================================
# 3. 공통 WS 핸들러 템플릿
# ============================================
print("\n[3] 공통 WS 구현 템플릿 생성")

ws_template = '''
# ============================================
# WebSocket 구현 (공통 패턴)
# ============================================

def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
    """웹소켓 시작 (봉 마감 + 실시간 가격)"""
    try:
        from exchanges.ws_handler import WSHandler
        
        self.ws_handler = WSHandler(
            exchange=self.name,
            symbol=self.symbol,
            interval=interval
        )
        
        # 콜백 등록
        if on_candle_close:
            self.ws_handler.on_candle_close = on_candle_close
        if on_price_update:
            self.ws_handler.on_price_update = on_price_update
        if on_connect:
            self.ws_handler.on_connect = on_connect
        
        # 연결 시작
        result = self.ws_handler.connect()
        
        if result:
            logging.info(f"[{self.name}] WebSocket connected")
        
        return result
        
    except Exception as e:
        logging.error(f"[{self.name}] WebSocket failed: {e}")
        return False

def stop_websocket(self):
    """웹소켓 중지"""
    if hasattr(self, 'ws_handler') and self.ws_handler:
        self.ws_handler.disconnect()
        logging.info(f"[{self.name}] WebSocket stopped")

def restart_websocket(self):
    """웹소켓 재시작"""
    self.stop_websocket()
    time.sleep(1)
    return self.start_websocket()
'''

print("  ✅ 공통 WS 템플릿 준비됨")

# ============================================
# 4. 자동 시간 동기화 템플릿
# ============================================
print("\n[4] 자동 시간 동기화 템플릿")

time_sync_template = '''
# ============================================
# API 시간 자동 동기화
# ============================================

def _auto_sync_time(self):
    """API 호출 전 자동 시간 동기화"""
    try:
        # 마지막 동기화 후 5분 이상 지났으면 재동기화
        if not hasattr(self, '_last_sync') or (time.time() - self._last_sync) > 300:
            self.sync_time()
            self._last_sync = time.time()
    except Exception:
        pass

def sync_time(self):
    """서버 시간과 동기화"""
    try:
        # 거래소별 시간 API
        if hasattr(self.exchange, 'fetch_time'):
            server_time = self.exchange.fetch_time()
            local_time = int(time.time() * 1000)
            self.time_offset = local_time - server_time
            logging.debug(f"[{self.name}] Time synced: offset={self.time_offset}ms")
            return True
    except Exception as e:
        logging.debug(f"[{self.name}] Time sync failed: {e}")
        self.time_offset = 0
    return False

def fetchTime(self):
    """서버 시간 조회 (없는 거래소는 로컬 시간)"""
    try:
        if hasattr(self.exchange, 'fetch_time'):
            return self.exchange.fetch_time()
    except Exception:
        pass
    return int(time.time() * 1000)
'''

print("  ✅ 자동 시간 동기화 템플릿 준비됨")

# ============================================
# 5. ws_handler.py 거래소별 지원 확인
# ============================================
print("\n[5] ws_handler.py 거래소 지원 상태")

ws_handler = base / 'exchanges' / 'ws_handler.py'
if ws_handler.exists():
    ws_code = ws_handler.read_text(encoding='utf-8', errors='ignore')
    
    exchanges_check = ['bybit', 'binance', 'upbit', 'bithumb', 'okx', 'bitget', 'bingx']
    for ex in exchanges_check:
        if ex in ws_code.lower():
            print(f"  {ex}: ✅ ws_handler에 파싱 로직 있음")
        else:
            print(f"  {ex}: ❌ ws_handler에 추가 필요")

# ============================================
# 6. 구현 계획
# ============================================
print("\n" + "=" * 60)
print("구현 계획")
print("=" * 60)

print("""
[Phase 1] ws_handler.py 확장
  - Binance WS 엔드포인트 + 파싱 추가
  - Upbit WS 엔드포인트 + 파싱 추가  
  - Bithumb WS 엔드포인트 + 파싱 추가
  - OKX/Bitget/BingX WS 추가

[Phase 2] 각 거래소 어댑터에 WS 연동
  - start_websocket 메서드 추가 (공통 템플릿)
  - stop_websocket, restart_websocket 추가

[Phase 3] 자동 시간 동기화
  - API 호출 전 _auto_sync_time 호출
  - 5분마다 자동 재동기화
  - PC 시간 drift 자동 보정

[Phase 4] 연결 상태 모니터링
  - is_healthy() 메서드로 WS 상태 체크
  - 30초 무응답 시 자동 재연결
  - REST fallback 지원

[결과]
  - 모든 거래소 동일한 방식으로 WS 지원
  - API 401 에러 자동 방지
  - 봉 마감 실시간 감지 (~100ms)
""")

print("\n진행할까요? (ws_handler.py 확장부터 시작)")
