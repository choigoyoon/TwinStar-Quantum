# 🔍 프로젝트 전체 분석 보고서

> **작성일**: 2025-12-21  
> **대상**: 활성 코드 (GUI, core, utils 폴더)  
> **총 Python 파일**: 1,249개 (백업 포함)

---

## 📊 문제 요약

| # | 카테고리 | 발견 건수 | 영향도 | 상태 |
|---|----------|----------|--------|------|
| 1 | 시간 동기화 | 56건 | 🔴 높음 | ⚠️ 혼용 |
| 2 | UI 미정의 | 1건 | 🔴 높음 | ✅ 수정완료 |
| 3 | 경로/파일 | 32건 | 🟡 중간 | ⚠️ 분산 |
| 4 | 프리셋 경로 | 243건 | 🟡 중간 | ⚠️ 확인필요 |
| 5 | JSON I/O | 102건 | 🟢 낮음 | ✅ 정상 |

---

## 1️⃣ 시간 동기화 문제 (🔴 높음)

### 발견된 패턴

| 사용 패턴 | 파일 | 라인 | 용도 |
|----------|------|------|------|
| `datetime.now()` | 대부분 | 다수 | 로컬 시간 (KST) |
| `datetime.utcnow()` | strategy_core.py | 312, 352 | 시그널 타임스탬프 |
| `datetime.utcnow()` | unified_bot.py | 1296, 1391 | 시그널/유효성 체크 |

### 🚨 혼용 지점 (위험)

```
┌─────────────────────────────────────────────────────────────┐
│                    시간 흐름 불일치                          │
├─────────────────────────────────────────────────────────────┤
│ strategy_core.py (L312, L352)                               │
│   → timestamp=datetime.utcnow()  ← UTC                     │
│                                                             │
│ unified_bot.py (L1391)                                      │
│   → now = datetime.utcnow()     ← UTC                      │
│   → signal.timestamp 비교                                   │
│                                                             │
│ unified_bot.py (L1741, L1990)                               │
│   → now = datetime.now()        ← KST (불일치!)            │
│   → "지난 X시간" 로그 출력                                   │
└─────────────────────────────────────────────────────────────┘
```

### 위험 시나리오
1. **시그널 유효성 오판**: UTC 시그널 vs KST 현재시간 비교 → 9시간 차이
2. **로그 시간 혼란**: 실제 UTC보다 9시간 후로 표시
3. **entry_validity_hours 오작동**: 4시간 유효가 실제로 13시간이 됨

### 수정 방안

```python
# 권장: 모두 UTC 통일
from datetime import datetime, timezone

def get_utc_now():
    return datetime.now(timezone.utc)

# 또는 KST 명시
KST = timezone(timedelta(hours=9))
def get_kst_now():
    return datetime.now(KST)
```

---

## 2️⃣ UI 미정의 문제 (✅ 수정완료)

### 수정된 항목

| 파일 | 속성 | 상태 |
|------|------|------|
| optimization_widget.py | `metric_combo` | ✅ 추가됨 |
| optimization_widget.py | `cpu_info_label` | ✅ 추가됨 |
| optimization_widget.py | `speed_combo` | ✅ 추가됨 |

---

## 3️⃣ 경로/파일 분석

### `paths.py` 구조

```python
class Paths:
    BASE = get_base_path()           # EXE 옆 또는 프로젝트 루트
    INTERNAL_BASE = get_internal_path()  # _MEIPASS 또는 프로젝트 루트
    
    # 고정 경로
    CONFIG = INTERNAL_BASE + '/config'      # 번들된 설정
    USER_CONFIG = BASE + '/config'          # 사용자 설정
    LOGS = BASE + '/logs'
    DATA = BASE + '/data'
    CACHE = DATA + '/cache'
    PRESETS = USER_CONFIG + '/presets'      # 프리셋 폴더
```

### Paths 사용 현황

| 파일 | 사용 경로 | 용도 |
|------|----------|------|
| unified_bot.py:22 | `Paths.LOGS` | 로그 파일 |
| unified_bot.py:532 | `Paths.CACHE` | 캔들 데이터 |
| unified_bot.py:565 | `Paths.PRESETS` | 프리셋 로드 |
| trading_dashboard.py:251 | `Paths.PRESETS` | 프리셋 목록 |
| trading_dashboard.py:676 | `Paths.CACHE` | 캐시 데이터 |
| multi_trader.py:128 | `Paths.PRESETS` | 프리셋 패턴 |
| multi_sniper.py:165 | `Paths.PRESETS` | 프리셋 로드 |
| preset_manager.py:20 | `Paths.USER_CONFIG` | 설정 경로 |

### ✅ 경로 일관성 확인

모든 활성 코드가 `Paths` 클래스를 통해 경로 접근 → **정상**

---

## 4️⃣ 프리셋 경로 분석

### 프리셋 관련 파일

| 파일 | 역할 |
|------|------|
| `utils/preset_manager.py` | 프리셋 저장/로드 중앙 관리 |
| `core/unified_bot.py` | 봇에서 프리셋 로드 |
| `core/multi_trader.py` | 멀티트레이더 프리셋 |
| `core/multi_sniper.py` | 스나이퍼 프리셋 |
| `GUI/trading_dashboard.py` | UI에서 프리셋 선택 |
| `GUI/optimization_widget.py` | 최적화 결과 → 프리셋 저장 |

### 프리셋 경로 구조

```
config/presets/
├── _default.json          # 기본 프리셋
├── bybit_btcusdt_optimized.json
├── binance_ethusdt_optimized.json
└── ...
```

### 프리셋 명명 규칙

```python
# unified_bot.py:565
preset_path = f"{exchange_name}_{symbol_clean}_optimized.json"

# optimization_widget.py:982
time_str = datetime.now().strftime("%m%d_%H%M")
filename = f"{symbol_clean}_{time_str}_{tf}.json"
```

### ⚠️ 잠재 문제

1. **명명 규칙 불일치**: `_optimized` vs `_{time}_{tf}` 형식
2. **프리셋 매칭 실패 가능**: 파일명 패턴이 달라 못 찾을 수 있음

---

## 5️⃣ JSON I/O 현황

### 파일별 JSON 사용

| 파일 | json.load | json.dump | 용도 |
|------|-----------|-----------|------|
| preset_manager.py | ✅ | ✅ | 프리셋 |
| constants.py | ✅ | ✅ | strategy_params |
| telegram_popup.py | ✅ | ✅ | 텔레그램 설정 |
| security.py | ✅ | ✅ | 보안 설정 |
| settings_widget.py | ✅ | ✅ | 앱 설정 |
| history_widget.py | ✅ | - | 거래 내역 |
| symbol_cache.py | ✅ | ✅ | 심볼 캐시 |

### ✅ 인코딩 일관성

대부분 `encoding='utf-8'` 사용 → **정상**

---

## 🔧 수정 우선순위

### 🔴 긴급 (즉시 수정)

| # | 문제 | 파일 | 수정 내용 |
|---|------|------|----------|
| 1 | UTC/KST 혼용 | unified_bot.py | datetime.now() → datetime.utcnow() 통일 |
| 2 | 시간 비교 오류 | unified_bot.py:1741, 1990 | UTC 기준으로 변경 |

### 🟡 중요 (이번 주 내)

| # | 문제 | 파일 | 수정 내용 |
|---|------|------|----------|
| 3 | 프리셋 명명 규칙 | optimization_widget.py | `_optimized` 접미사 사용 |
| 4 | 프리셋 매칭 로직 | CoinRow._load_presets | 패턴 매칭 개선 |

### 🟢 권장 (시간 될 때)

| # | 문제 | 파일 | 수정 내용 |
|---|------|------|----------|
| 5 | 시간 유틸리티 | 신규 생성 | `utils/time_utils.py` 공통 함수 |
| 6 | 경로 검증 | paths.py | 시작 시 폴더 존재 확인 |

---

## 📋 수정 순서 체크리스트

```
✅ 1. unified_bot.py 시간 통일 완료
  - L1129, L1759, L2008, L2563: datetime.now() → datetime.utcnow()
  
✅ 2. 시간 유틸리티 생성 완료
  - utils/time_utils.py 생성
  - get_utc_now(), get_kst_now(), get_exchange_now() 등
  - is_signal_valid() 시그널 유효성 검사
  
□ 3. 프리셋 명명 규칙 통일
  - optimization_widget.py에서 저장 시 `_optimized` 사용
  
□ 4. 전체 테스트
  - 봇 시작/종료
  - 시그널 유효성 체크
  - 프리셋 로드/저장
```

---

## 📎 관련 문서

- [gui_widget_analysis.md](./gui_widget_analysis.md) - GUI 위젯 분석
- [paths.py](../paths.py) - 경로 정의

---

> **다음 작업**: `unified_bot.py` 시간 통일 수정 진행?
