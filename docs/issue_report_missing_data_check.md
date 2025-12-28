# 이슈 보고서: GUI 데이터 자동 수집 알림 기능 누락

**작성일:** 2025-12-20
**상태:** ⚠️ 확인 필요 (구현 누락)
**관련 파일:** `GUI/trading_dashboard.py`, `core/unified_bot.py`

---

## 1. 개요
봇 시작 시 로컬 캐시 데이터(`parquet`)가 존재하지 않을 경우, 사용자가 이를 인지하고 데이터를 수집할 수 있도록 안내하는 기능이 Phase 4 기획 단계에서 논의되었으나, 현재 **GUI 코드에 반영되지 않은 상태**임이 확인되었습니다.

## 2. 현재 상태 분석

### 2.1. `core/unified_bot.py` (✅ 정상)
봇 코어 로직에는 데이터 존재 여부를 확인하는 메서드가 구현되어 있습니다.
- **메서드명**: `_check_data_exists()`
- **기능**: 필수 데이터 파일(15m, 1h 등)의 존재 여부를 리턴

### 2.2. `GUI/trading_dashboard.py` (❌ 누락)
GUI에서 봇을 시작하는 `toggle_bot` (또는 `start_bot`) 메서드 내부에서 위 `_check_data_exists()` 결과를 확인하고 처리하는 로직이 **전혀 없습니다.**
- `findstr` 검색 결과: `_check_data_exists`, `자동 수집` 키워드 없음.
- **결과**: 데이터가 없어도 봇 프로세스는 시작되지만, 내부적으로 데이터 로드 실패로 인해 신호가 발생하지 않음 (`Pending=0`).

---

## 3. 누락된 기능 상세
Phase 4 기획에 따르면 다음과 같은 흐름이어야 합니다.

1. 사용자가 **[Start Bot]** 클릭
2. GUI가 `bot._check_data_exists()` 호출
3. **데이터 없음 (`False`) 반환 시**:
    - 팝업 표시: "매매 데이터가 부족합니다. 자동으로 수집하시겠습니까?"
    - **[Yes]**: 데이터 수집기(`DataCollector`) 실행 후 봇 시작
    - **[No]**: 봇 시작 취소

---

## 4. 구현 제안 (코드 수정안)

`GUI/trading_dashboard.py` 파일의 봇 시작 로직(`_toggle_bot` 추정)에 다음 코드를 삽입해야 합니다.

```python
def _toggle_bot(self):
    # ... (봇 인스턴스 확인)
    
    if not self.bot.is_running:
        # 1. [NEW] 데이터 존재 여부 확인
        data_status = self.bot._check_data_exists()  # unified_bot.py의 메서드 호출
        
        if not data_status.get('ready', False):
            reply = QMessageBox.question(
                self, 
                "데이터 부족",
                f"매매에 필요한 데이터가 없습니다.\n({data_status.get('missing', '데이터 확인 필요')})\n\n자동으로 수집하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self._start_auto_collection()  # 수집 후 봇 시작 로직 연결
                return
            else:
                return  # 시작 취소
        
        # 2. 기존 시작 로직 계속 진행
        self.bot.start()
        # ...
```

## 5. 조치 계획 (Action Plan)

1. `GUI/trading_dashboard.py` 파일 열기
2. 봇 시작 메서드(`_toggle_bot`) 위치 파악
3. 누락된 데이터 체크 및 알림 로직 추가
4. `_start_auto_collection` 헬퍼 메서드 추가 (또는 기존 수집기 호출 연결)
5. 테스트 및 빌드

---

**결론**: 기능 누락이 명확하므로, 즉시 `GUI/trading_dashboard.py` 수정 작업이 필요합니다.
