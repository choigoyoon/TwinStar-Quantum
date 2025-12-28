
from pathlib import Path

binance_file = Path(r'C:\매매전략\exchanges\binance_exchange.py')
code = binance_file.read_text(encoding='utf-8')

ws_code = '''
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
            for task in asyncio.all_tasks():
                if 'connect' in str(task):
                    task.cancel()
            import logging
            logging.info("[Binance] WebSocket stopped")
    
    async def restart_websocket(self):
        """웹소켓 재시작"""
        self.stop_websocket()
        import asyncio
        await asyncio.sleep(1)
        return await self.start_websocket()
'''

if 'start_websocket' in code:
    print("Already exists")
else:
    new_code = code + ws_code
    binance_file.write_text(new_code, encoding='utf-8')
    print("WS code appended successfully")
