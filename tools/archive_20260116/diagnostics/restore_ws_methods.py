
from pathlib import Path

# Common WS Code Template
ws_code_template = '''
    # ============================================
    # WebSocket + 자동 시간 동기화 (Phase 2+3)
    # ============================================
    
    async def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
        """웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler(
                exchange='{exchange_key}', 
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

def restore_exchange(file_path, exchange_name, exchange_key, alias_line_prefix):
    path = Path(file_path)
    if not path.exists():
        print(f"❌ {file_path} not found")
        return

    code = path.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    # 1. Clean up potential leftovers or alias
    # Remove lines from '# ============================================' downwards
    clean_lines = []
    found_marker = False
    for line in lines:
        if '# ============================================' in line:
            found_marker = True # Stop adding lines here, but we might want the code before this
            break # Assume everything after was our broken append
        
        # Also stop if we hit the alias line, we will re-add it manually
        if line.strip().startswith(alias_line_prefix):
            break
            
        clean_lines.append(line)
    
    # Trim trailing empty lines
    while clean_lines and not clean_lines[-1].strip():
        clean_lines.pop()
        
    cleaned_code = '\n'.join(clean_lines)
    
    # 2. Prepare new code
    ws_code = ws_code_template.replace('{exchange_name}', exchange_name).replace('{exchange_key}', exchange_key)
    
    # 3. Re-assemble: clean code + ws code + alias
    # Find exact alias line from original code to be safe, or just reconstruct it
    # We know the alias structure.
    
    if exchange_key == 'okx':
        alias_str = "OkxExchange = OKXExchange"
    elif exchange_key == 'bingx':
        alias_str = "BingxExchange = BingXExchange" # Check if this is correct
        
        # Verify BingX alias in original file if possible
        if "BingXExchange = BingxExchange" in code:
             alias_str = "BingXExchange = BingxExchange"
    
    final_content = cleaned_code + '\n' + ws_code + '\n\n' + alias_str
    
    path.write_text(final_content, encoding='utf-8')
    print(f"✅ Restored {exchange_name}")

# Restore OKX
restore_exchange(r'C:\매매전략\exchanges\okx_exchange.py', 'Okx', 'okx', 'OkxExchange =')

# Restore BingX
restore_exchange(r'C:\매매전략\exchanges\bingx_exchange.py', 'Bingx', 'bingx', 'BingxExchange =') # Attempt with likely prefix
