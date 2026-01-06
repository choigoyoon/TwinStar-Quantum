# 자동매매 파이프라인(V2.0) 개발자 관점 갭 분석 리포트

> [!WARNING]
> 현재 구현된 파이프라인은 UI 및 워크플로우 검증용 **Mock(모의) 로직**이 다수 포함되어 있습니다. 실전 매매를 위해서는 아래 기능들의 **실제 구현체 교체**가 필수적입니다.

## 1. 갭 분석 결과 (Gap Analysis)

### Step 1: 심볼 선택 (Symbol Selection)
- **현재 상태**: `dummy_symbols` 및 하드코딩된 Top 10 리스트 사용.
- **필요 조치**: `ExchangeFactory`를 통해 실제 거래소(비트겟, 바이낸스, OKX)의 API를 호출하여 **실시간 거래량 상위 심볼**을 가져오도록 수정해야 함.
- **영향도**: 높음 (실제 상장된 심볼을 불러오지 못하면 최적화 불가)

### Step 4: 스캐너 설정 (Configuration)
- **현재 상태**: 설정값이 메모리에만 존재하며, 재시작 시 초기화됨.
- **필요 조치**: `config.json` 또는 `scanner_config.json` 파일에 설정값을 저장하고 로드하는 로직 추가 필요.
- **영향도**: 중간 (사용자 편의성)

### Step 5: 실전 매매 (AutoScanner Core)
- **현재 상태**:
    - **시그널 탐지**: `random` 모듈을 사용하여 5% 확률로 가짜 시그널 발생.
    - **주문 실행**: 실제 주문 API(`create_order`) 호출 없이 로그만 출력.
    - **포지션 관리**: 메모리 내 `active_positions` 딕셔너리로 관리되며, 실제 잔고나 포지션 동기화 없음.
- **필요 조치**:
    - `AlphaX7Core` 전략 모듈을 연동하여 실제 캔들 데이터(`get_klines`) 기반 시그널 계산.
    - `DualTrackTrader` 또는 `UnifiedBot` 인스턴스를 활용하여 실제 주문 실행.
    - 웹소켓 또는 REST API 폴링을 통해 실제 포지션 상태 동기화.
- **영향도**: **치명적** (이대로는 실매매 불가)

### 기타 (Logging)
- **현재 상태**: GUI 텍스트 영역에만 로그 출력.
- **필요 조치**: `logging` 모듈을 사용하여 `logs/auto_scanner.log` 등 파일로 기록 남김 필요.

---

## 2. 개선 계획 (Action Plan)

개발자 모드로 전환하여 다음 순서로 실제 로직을 구현하겠습니다.

1.  **Step 1 리팩토링**: `GUI/auto_pipeline_widget.py` 수정
    - `ExchangeFactory` 연동
2.  **AutoScanner 리팩토링**: `core/auto_scanner.py` 수정
    - `random` 기반 로직 제거
    - `AlphaX7Core` (전략) 및 거래소 실행 모듈 연동
3.  **검증**: 실제 API 호출 테스트 (Dry Run 모드)
