
from pathlib import Path

binance_file = Path(r'C:\매매전략\exchanges\binance_exchange.py')
code = binance_file.read_text(encoding='utf-8')

# Phase 3: 자동 시간 동기화 코드
time_sync_code = '''
    def _auto_sync_time(self):
        """API 호출 전 자동 시간 동기화 (5분마다)"""
        import time
        if not hasattr(self, '_last_sync'):
            self._last_sync = 0
        
        if time.time() - self._last_sync > 300:
            self.sync_time()
            self._last_sync = time.time()
            
    def fetchTime(self):
        """서버 시간 조회 (통일된 인터페이스)"""
        import time
        try:
            if self.client:
                server_time = self.client.get_server_time()
                return server_time['serverTime']
        except Exception:
            pass
        return int(time.time() * 1000)
'''

if 'def fetchTime' in code:
    print("Already exists")
else:
    new_code = code + time_sync_code
    binance_file.write_text(new_code, encoding='utf-8')
    print("Binance time sync methods added successfully")
