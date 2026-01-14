
from pathlib import Path

base = Path(__file__).parent
binance_file = base / 'exchanges' / 'binance_exchange.py'

print("=" * 60)
print("Phase 2: Binance 어댑터 WS 연동")
print("=" * 60)

# 1. 현재 binance_exchange.py 구조 확인
code = binance_file.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

print("\n[1] 현재 메서드 목록")
for i, line in enumerate(lines):
    if 'def ' in line and '(self' in line:
        print(f"  L{i+1}: {line.strip()[:60]}")

# 2. start_websocket 존재 여부
print("\n[2] WS 관련 메서드")
has_start_ws = 'def start_websocket' in code
has_stop_ws = 'def stop_websocket' in code

print(f"  start_websocket: {'✅ 있음' if has_start_ws else '❌ 없음'}")
print(f"  stop_websocket: {'✅ 있음' if has_stop_ws else '❌ 없음'}")

# 3. 클래스 끝 위치 찾기 (메서드 추가 위치)
print("\n[3] 클래스 구조")
class_start = None
last_method = None
for i, line in enumerate(lines):
    if 'class ' in line and 'Exchange' in line:
        class_start = i
        print(f"  L{i+1}: 클래스 시작 - {line.strip()[:50]}")
    if class_start and 'def ' in line and '(self' in line:
        last_method = i

if last_method:
    print(f"  L{last_method+1}: 마지막 메서드")

# 4. 추가할 WS 코드
print("\n[4] 추가할 코드")

ws_code_to_add = '''
    # ============================================
    # WebSocket 연동 (Phase 2)
    # ============================================
    
    async def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
        """Binance 웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler(
                exchange='binance',
                symbol=self.symbol,
                interval=interval
            )
            
            # 콜백 등록
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect
            
            # 연결 (비동기 태스크로 실행)
            import asyncio
            asyncio.create_task(self.ws_handler.connect())
            
            import logging
            logging.info(f"[Binance] WebSocket started: {self.symbol} {interval}")
            return True
            
        except Exception as e:
            import logging
            logging.error(f"[Binance] WebSocket failed: {e}")
            return False
    
    def stop_websocket(self):
        """웹소켓 중지"""
        if hasattr(self, 'ws_handler') and self.ws_handler:
            self.ws_handler.disconnect()
            import logging
            logging.info("[Binance] WebSocket stopped")
    
    async def restart_websocket(self):
        """웹소켓 재시작"""
        self.stop_websocket()
        import asyncio
        await asyncio.sleep(1)
        return await self.start_websocket()
'''

print(ws_code_to_add)

# 5. 자동 추가 여부
print("\n" + "=" * 60)
print("Binance 어댑터에 위 코드를 추가할까요?")
print("=" * 60)
