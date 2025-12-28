# 이슈 보고서: 데이터 최신성 체크 로직 강화 제안

**작성일:** 2025-12-20
**분석 결과:** 기존 기능 존재, BUT 로직 불완전
**관련 파일:** `GUI/trading_dashboard.py`

---

## 1. 현상 분석

사용자는 "수집 데이터가 없으면 자동 수집해야 하는데 안 된다"고 리포트했습니다. 그러나 소스 코드 확인 결과, `_check_bot_readiness` 메서드가 이미 존재하며 파일 존재 여부(`os.path.exists`)를 확인하고 있습니다.

로그 분석 결과(`[INIT] Loaded 35040 15m candles`), 봇은 실제로 과거 데이터를 로드했습니다. 즉, **파일이 존재하기 때문에** 기존 로직상으로는 "준비 완료"로 판단되어 자동 수집 팝업이 뜨지 않은 것입니다.

**문제의 핵심:** 
파일이 존재하더라도 그 데이터가 **오래된 데이터(Outdated)**일 경우, 봇은 최신 시장 상황을 모르기 때문에 매매 신호를 발생시키지 못합니다(Pending=0).

## 2. 해결 방안: 최신성(Recency) 체크 추가

단순히 "파일이 있는가?"만 체크하는 것이 아니라, **"파일이 최신인가?"**를 체크해야 합니다.

### 권장 수정 로직 (`trading_dashboard.py`)

`_check_bot_readiness` 메서드에 다음 로직을 추가합니다.

1. 파일 수정 시간(`mtime`) 확인
2. 현재 시간과 비교하여 **1시간 이상 경과**했으면 "업데이트 필요"로 간주
3. 팝업을 통해 데이터 수집 유도

---

## 3. 구현 상세 (Code Proposal)

`GUI/trading_dashboard.py`의 `_check_bot_readiness` 메서드를 다음과 같이 개선합니다.

```python
    def _check_bot_readiness(self, exchange: str, symbol: str) -> bool:
        """봇 시작 전 데이터/최적화 준비 상태 확인 (최신성 체크 추가)"""
        from paths import Paths
        import os
        import time  # 시간 모듈 필요
        
        exchange_lower = exchange.lower()
        symbol_clean = symbol.lower().replace('/', '').replace('-', '')
        
        # 1. 데이터 파일 확인
        data_15m = os.path.join(Paths.CACHE, f"{exchange_lower}_{symbol_clean}_15m.parquet")
        data_1h = os.path.join(Paths.CACHE, f"{exchange_lower}_{symbol_clean}_1h.parquet")
        
        missing_data = []
        current_time = time.time()
        expiry_seconds = 3600  # 1시간 이상 지나면 구형 데이터로 간주
        
        # 15m 데이터 체크
        if not os.path.exists(data_15m) or os.path.getsize(data_15m) < 10240:
            missing_data.append("15m (없음)")
        elif (current_time - os.path.getmtime(data_15m)) > expiry_seconds:
            missing_data.append("15m (업데이트)")
            
        # 1h 데이터 체크
        if not os.path.exists(data_1h) or os.path.getsize(data_1h) < 10240:
            missing_data.append("1h (없음)")
        elif (current_time - os.path.getmtime(data_1h)) > expiry_seconds:
             missing_data.append("1h (업데이트)")
        
        if missing_data:
            # 팝업 표시 (기존 메서드 활용)
            if not self._show_data_collect_dialog(exchange, symbol, missing_data):
                return False
        
        # ... (최적화 프리셋 체크 로직 유지)
```

## 4. 기대 효과

*   오래된 캐시 파일만 있는 경우에도 사용자가 이를 인지하고 **[Yes]**를 눌러 최신 데이터를 받을 수 있게 됩니다.
*   "데이터가 있는데 매매 안 함" 문제를 "데이터 업데이트 후 정상 매매"로 유도할 수 있습니다.

---

**Action Item:** 위 로직을 `GUI/trading_dashboard.py`에 적용 후 재빌드.
