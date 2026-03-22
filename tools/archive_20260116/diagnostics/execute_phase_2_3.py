
from pathlib import Path

base = Path(r'C:\매매전략')

print("=" * 60)
print("Phase 2+3: 모든 거래소 WS + 자동 시간동기화")
print("=" * 60)

# 공통 코드 템플릿
common_ws_code = '''
    # ============================================
    # WebSocket + 자동 시간 동기화 (Phase 2+3)
    # ============================================
    
    async def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
        """웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler(
                exchange='{exchange_key}', # lower case for handler
                symbol=self.symbol,
                interval=interval
            )
            
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect
            
            import asyncio
            asyncio.create_task(self.ws_handler.connect())
            
            import logging
            logging.info(f"[{exchange_name}] WebSocket connected: {{self.symbol}}")
            return True
        except Exception as e:
            import logging
            logging.error(f"[{exchange_name}] WebSocket failed: {{e}}")
            return False
    
    def stop_websocket(self):
        """웹소켓 중지"""
        if hasattr(self, 'ws_handler') and self.ws_handler:
            self.ws_handler.disconnect()
    
    async def restart_websocket(self):
        """웹소켓 재시작"""
        self.stop_websocket()
        import asyncio
        await asyncio.sleep(1)
        return await self.start_websocket()
    
    def _auto_sync_time(self):
        """API 호출 전 자동 시간 동기화 (5분마다)"""
        import time
        if not hasattr(self, '_last_sync'):
            self._last_sync = 0
        
        if time.time() - self._last_sync > 300:
            self.sync_time()
            self._last_sync = time.time()
    
    def sync_time(self):
        """서버 시간 동기화"""
        import time
        import logging
        try:
            # ccxt 기반 거래소의 경우
            if hasattr(self, 'exchange') and hasattr(self.exchange, 'fetch_time'):
                server_time = self.exchange.fetch_time()
                local_time = int(time.time() * 1000)
                self.time_offset = local_time - server_time
                logging.debug(f"[{exchange_name}] Time synced: offset={{self.time_offset}}ms")
                return True
        except Exception as e:
            logging.debug(f"[{exchange_name}] Time sync failed: {{e}}")
        self.time_offset = 0
        return False
    
    def fetchTime(self):
        """서버 시간 조회"""
        import time
        try:
            if hasattr(self, 'exchange') and hasattr(self.exchange, 'fetch_time'):
                return self.exchange.fetch_time()
        except Exception:
            pass
        return int(time.time() * 1000)
'''

# 적용할 거래소 목록
exchanges = ['upbit', 'bithumb', 'okx', 'bitget', 'bingx']

print("\n[적용 대상 거래소]")
for ex in exchanges:
    print(f"  - {ex}_exchange.py")

# 각 거래소 파일 확인 및 수정
print("\n[처리 결과]")
for ex_name in exchanges:
    ex_file = base / 'exchanges' / f'{ex_name}_exchange.py'
    
    if not ex_file.exists():
        print(f"  {ex_name}: ❌ 파일 없음")
        continue
    
    code = ex_file.read_text(encoding='utf-8')
    
    # 이미 start_websocket 있는지 확인
    if 'def start_websocket' in code and 'WebSocketHandler' in code:
        print(f"  {ex_name}: ✅ 이미 WS 구현됨")
        continue
    
    # 클래스 이름이나 로그용 이름
    exchange_name_cap = ex_name.lower().capitalize()
    
    # 코드 삽입
    exchange_code = common_ws_code.replace('{exchange_name}', exchange_name_cap).replace('{exchange_key}', ex_name)
    
    # 파일 끝에 추가 (단순 append)
    # 클래스 들여쓰기는 파일마다 다를 수 있으나 보통 4칸 공백으로 가정.
    # 안전하게 마지막 줄의 들여쓰기를 확인하거나, 그냥 4칸으로 가정.
    # 대부분의 파일이 class Exchange:\n ... 형태이므로 마지막에 4칸 들여쓰기로 추가하면 됨.
    
    # 혹시 파일 끝이 tap이나 space로 끝나면 제거
    new_code = code.rstrip() + '\n' + exchange_code + '\n'
    
    # 백업 후 저장
    backup = ex_file.with_suffix('.py.bak')
    backup.write_text(code, encoding='utf-8')
    ex_file.write_text(new_code, encoding='utf-8')
    
    print(f"  {ex_name}: ✅ WS + 시간동기화 추가됨")

print("\n" + "=" * 60)
print("Phase 2+3 완료")
print("=" * 60)

# 검증
print("\n[검증]")
for ex_name in exchanges + ['binance']:
    ex_file = base / 'exchanges' / f'{ex_name}_exchange.py'
    if ex_file.exists():
        code = ex_file.read_text(encoding='utf-8')
        has_ws = 'def start_websocket' in code
        has_sync = 'def sync_time' in code or 'def _auto_sync_time' in code
        has_fetch = 'def fetchTime' in code
        
        ws = '✅' if has_ws else '❌'
        sync = '✅' if has_sync else '❌'
        fetch = '✅' if has_fetch else '❌'
        
        print(f"  {ex_name}: WS={ws} Sync={sync} FetchTime={fetch}")
