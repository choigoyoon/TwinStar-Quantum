# 전체 프로젝트 일관성 점검 리포트

## 요약
| 항목 | 점검 카테고리 | 상태 |
|------|--------------|------|
| 1 | 데이터 흐름 | ✅ 일관됨 (수정 후) |
| 2 | 파라미터 전달 | ✅ 일관됨 |
| 3 | 파일 저장/로드 | ✅ 일관됨 |
| 4 | API 호출 방식 | ✅ 일관됨 (수정 후) |
| 5 | 에러 핸들링 | ⚠️ 부분 불일치 |
| 6 | 로깅 방식 | ⚠️ 부분 불일치 |
| 7 | 설정 관리 | ✅ 일관됨 |

**총점: 5/7 완전 일관, 2/7 부분 불일치**

---

## 상세

### 1. 데이터 흐름 ✅
- **15m 단일 소스**: 적용됨
- **리샘플링 위치**: `utils/data_utils.resample_data()`
- **수정 완료**:
  - `auto_scanner.py`: 15m → 4H resample
  - `unified_backtest.py`: 15m → 1H resample

### 2. 파라미터 전달 ✅
- **소스**: `config/parameters.py → DEFAULT_PARAMS`
- **전달 흐름**:
  ```
  config.parameters.DEFAULT_PARAMS
    ↓
  preset_manager.load_preset_flat()
    ↓
  optimizer / backtest / scanner / bot 사용
  ```
- **일관성**: 모든 모듈이 `preset_manager` 통해 접근

### 3. 파일 저장/로드 ✅
- **경로 중앙관리**: `paths.py → Paths 클래스`
- **주요 경로**:
  | 용도 | 경로 |
  |------|------|
  | 캔들 캐시 | `Paths.CACHE` = `data/cache` |
  | 프리셋 | `Paths.PRESETS` = `config/presets` |
  | 로그 | `Paths.LOGS` = `logs/` |
  | API 키 | `Paths.CREDENTIALS` = `user/global/credentials` |

### 4. API 호출 방식 ✅
- **관리 위치**: `exchanges/*.py`
- **단일 인터페이스**: `get_klines()`, `get_balance()` 등 통일
- **수정 완료**: core 모듈에서 4H/1H 직접 호출 제거

### 5. 에러 핸들링 ⚠️
- **try/except**: 사용됨
- **불일치**: 일부 에러가 print()로만 출력
- **권장**: logging.error() 통일

### 6. 로깅 방식 ⚠️
- **현황**: print()와 logging.info() 혼용
- **불일치 건수**: core/ 폴더 내 ~100개 print() 호출
- **권장**: 운영 코드는 logging 통일

### 7. 설정 관리 ✅
- **중앙 관리**: `config/parameters.py`
- **접근 방식**: `get_param()` 함수 제공
- **기본값**: `DEFAULT_PARAMS` dict

---

## 수정 필요 목록

| 우선순위 | 파일 | 문제 | 조치 |
|----------|------|------|------|
| LOW | core/*.py | print() 사용 | logging으로 통일 (선택) |
| LOW | 일부 에러 | print()로 출력 | logging.error() 사용 |

---

## 결론

> **수정 불필요, 진행 가능** ✅
>
> 핵심 기능(데이터, 파라미터, 경로, API)은 모두 일관됨.
> 로깅 혼용(print/logging)은 운영에 지장 없음.
