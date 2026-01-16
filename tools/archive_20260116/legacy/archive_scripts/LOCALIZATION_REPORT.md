# TwinStar Quantum 다국어 지원 구현 보고서
> 생성일: 2025-12-19 13:39

---

## 1. 개요

TwinStar Quantum v1.0.0에 한국어/영어 전환 기능이 추가되었습니다.

### 지원 언어

| 코드 | 언어 | 플래그 |
|------|------|:------:|
| `ko` | 한국어 | 🇰🇷 |
| `en` | English | 🇺🇸 |

---

## 2. 파일 구조

```
c:\매매전략\
├── locales/
│   ├── __init__.py         # 모듈 초기화 (167 B)
│   ├── lang_manager.py     # 언어 관리자 (6.1 KB)
│   ├── ko.json             # 한국어 번역 (5.6 KB)
│   └── en.json             # 영어 번역 (5.3 KB)
├── GUI/
│   ├── trading_dashboard.py  # t() import 추가
│   ├── backtest_widget.py    # t() import 추가
│   └── settings_widget.py    # 언어 선택 UI 추가
└── staru_clean.spec          # locales 포함 설정
```

---

## 3. 핵심 컴포넌트

### 3.1 LangManager 클래스

```python
from locales import t, set_language, get_lang_manager

# 번역 텍스트 가져오기
label_text = t("dashboard.exchange")  # "거래소" 또는 "Exchange"

# 언어 변경
set_language("en")  # 영어로 변경
set_language("ko")  # 한국어로 변경

# 현재 언어 확인
lang_mgr = get_lang_manager()
current = lang_mgr.current_language()  # "ko" 또는 "en"
```

### 3.2 번역 키 구조

```json
{
    "app": { "title": "...", "version": "..." },
    "menu": { "dashboard": "...", "backtest": "..." },
    "dashboard": { "exchange": "...", "symbol": "..." },
    "backtest": { "run": "...", "trades": "..." },
    "optimization": { "start": "...", "stop": "..." },
    "data": { "download": "...", "complete": "..." },
    "settings": { "api_key": "...", "language": "..." },
    "common": { "confirm": "...", "cancel": "..." },
    "log": { "pattern": "...", "detected": "..." },
    "trade": { "entry": "...", "exit": "..." },
    "message": { "restart_required": "...", "save_success": "..." }
}
```

---

## 4. 번역 키 목록

### 4.1 메뉴 (menu)

| 키 | 한국어 | English |
|----|--------|---------|
| `menu.dashboard` | 대시보드 | Dashboard |
| `menu.backtest` | 백테스트 | Backtest |
| `menu.optimization` | 최적화 | Optimization |
| `menu.data` | 데이터 | Data |
| `menu.settings` | 설정 | Settings |

### 4.2 대시보드 (dashboard)

| 키 | 한국어 | English |
|----|--------|---------|
| `dashboard.exchange` | 거래소 | Exchange |
| `dashboard.symbol` | 심볼 | Symbol |
| `dashboard.amount` | 금액 | Amount |
| `dashboard.leverage` | 레버리지 | Leverage |
| `dashboard.preset` | 프리셋 | Preset |
| `dashboard.start_bot` | 봇 시작 | Start Bot |
| `dashboard.stop_bot` | 봇 정지 | Stop Bot |
| `dashboard.bot_log` | 봇 로그 | Bot Log |
| `dashboard.realtime_log` | 실시간 로그 | Real-time Log |

### 4.3 백테스트 (backtest)

| 키 | 한국어 | English |
|----|--------|---------|
| `backtest.run` | 백테스트 실행 | Run Backtest |
| `backtest.load` | 불러오기 | Load |
| `backtest.trades` | 거래 | Trades |
| `backtest.win_rate` | 승률 | Win Rate |
| `backtest.mdd` | MDD | MDD |
| `backtest.refresh` | 새로고침 | Refresh |
| `backtest.save` | 저장 | Save |
| `backtest.delete` | 삭제 | Delete |

### 4.4 설정 (settings)

| 키 | 한국어 | English |
|----|--------|---------|
| `settings.api_key` | API 키 | API Key |
| `settings.secret_key` | 시크릿 키 | Secret Key |
| `settings.passphrase` | 패스프레이즈 | Passphrase |
| `settings.test_connection` | 연결 테스트 | Test Connection |
| `settings.language` | 언어 | Language |
| `settings.save` | 저장 | Save |

### 4.5 공통 (common)

| 키 | 한국어 | English |
|----|--------|---------|
| `common.confirm` | 확인 | Confirm |
| `common.cancel` | 취소 | Cancel |
| `common.error` | 오류 | Error |
| `common.warning` | 경고 | Warning |
| `common.success` | 성공 | Success |

### 4.6 메시지 (message)

| 키 | 한국어 | English |
|----|--------|---------|
| `message.restart_required` | 프로그램을 재시작해주세요 | Please restart the application |
| `message.save_success` | 저장되었습니다 | Saved successfully |
| `message.delete_confirm` | 정말 삭제하시겠습니까? | Are you sure you want to delete? |

---

## 5. GUI 적용 가이드

### 5.1 Import 추가

각 GUI 파일 상단에 추가:

```python
# 다국어 지원
try:
    from locales import t
except ImportError:
    def t(key, default=None):
        return default if default else key.split('.')[-1]
```

### 5.2 레이블 적용

**변경 전:**
```python
QLabel("거래소:")
QPushButton("봇 시작")
QMessageBox.warning(self, "오류", "데이터가 없습니다")
```

**변경 후:**
```python
QLabel(t("dashboard.exchange") + ":")
QPushButton(t("dashboard.start_bot"))
QMessageBox.warning(self, t("common.error"), t("backtest.no_data"))
```

### 5.3 기본값 지정

번역이 없을 경우를 대비:

```python
t("some.key", "Default Text")  # 키가 없으면 "Default Text" 반환
```

---

## 6. Settings UI

### 언어 선택 섹션

Settings 탭 상단에 Language 섹션이 추가되었습니다:

```
┌─ Language ────────────────────────────────────────┐
│ 🌐 [🇰🇷 한국어 ▼]  Language changed. Please restart. │
└────────────────────────────────────────────────────┘
```

### 동작 방식

1. 드롭다운에서 언어 선택
2. `config/settings.json`에 저장
3. 재시작 안내 메시지 표시
4. 프로그램 재시작 시 새 언어 적용

---

## 7. PyInstaller 설정

### staru_clean.spec 변경사항

```python
# datas 섹션
datas=[
    # ... 기존 항목 ...
    ('locales/*.json', 'locales'),  # 다국어 파일 추가
],

# hiddenimports 섹션
hiddenimports=[
    # ... 기존 항목 ...
    'locales', 'locales.lang_manager',  # 다국어 모듈 추가
],
```

---

## 8. 언어 설정 저장

설정은 `config/settings.json`에 저장됩니다:

```json
{
    "language": "ko"
}
```

---

## 9. 테스트 결과

```bash
$ py -c "from locales import t, set_language; set_language('ko'); print(t('dashboard.exchange'))"
거래소

$ py -c "from locales import t, set_language; set_language('en'); print(t('dashboard.exchange'))"
Exchange
```

---

## 10. 향후 확장

### 새 언어 추가 방법

1. `locales/` 폴더에 `{lang_code}.json` 파일 생성
2. `ko.json` 구조를 복사하여 번역
3. `LangManager.get_available_languages()`에 언어 정보 추가

### 예: 일본어 추가

```python
# lang_manager.py
def get_available_languages(self) -> list:
    return [
        {'code': 'ko', 'name': '한국어', 'flag': '🇰🇷'},
        {'code': 'en', 'name': 'English', 'flag': '🇺🇸'},
        {'code': 'ja', 'name': '日本語', 'flag': '🇯🇵'},  # 추가
    ]
```

```json
// locales/ja.json
{
    "dashboard": {
        "exchange": "取引所",
        "symbol": "シンボル",
        ...
    }
}
```

---

## 11. 수정된 파일 요약

| 파일 | 변경 내용 | 라인 |
|------|-----------|------|
| `locales/__init__.py` | 새로 생성 | 4 |
| `locales/lang_manager.py` | 새로 생성 | 180 |
| `locales/ko.json` | 새로 생성 | 160 |
| `locales/en.json` | 새로 생성 | 160 |
| `GUI/trading_dashboard.py` | import 추가 | +7 |
| `GUI/backtest_widget.py` | import 추가 | +7 |
| `GUI/settings_widget.py` | 언어 UI + 핸들러 | +45 |
| `staru_clean.spec` | datas, hiddenimports | +5 |

---

## 12. 다음 단계

1. [ ] 나머지 GUI 파일에 `t()` 적용
2. [ ] 모든 하드코딩된 문자열 번역 키로 교체
3. [ ] 빌드 및 테스트
4. [ ] 추가 언어 지원 (일본어, 중국어 등)

---

*보고서 끝*
