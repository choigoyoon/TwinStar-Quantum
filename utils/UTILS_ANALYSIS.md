# Utils 디렉토리 분석

## 현황
- **총 파일**: 28개
- **크기**: 417KB
- **상태**: 대부분 프로덕션 사용 중

## 사용 현황 분석

### ✅ 핵심 SSOT (3개) - 필수
| 파일 | 크기 | 용도 | 사용 |
|------|------|------|------|
| indicators.py | 18KB | 지표 계산 SSOT (v7.14) | ★★★★★ |
| metrics.py | 26KB | 메트릭 계산 SSOT (v7.4) | ★★★★★ |
| incremental_indicators.py | 9.4KB | 실시간 증분 계산 (v7.15) | ★★★★★ |

### ✅ 데이터 처리 (5개) - 필수
| 파일 | 크기 | 용도 | 사용 빈도 |
|------|------|------|----------|
| data_utils.py | 5.4KB | 데이터 변환/리샘플링 | 높음 |
| data_downloader.py | 5.8KB | OHLCV 데이터 다운로드 | 높음 |
| cache_manager.py | 7.1KB | 캐시 관리 | 높음 |
| cache_cleaner.py | 3.5KB | 캐시 정리 | 중간 |
| symbol_converter.py | 3.2KB | 심볼 변환 | 낮음 (1회) |

### ✅ 프리셋 관리 (2개) - 필수
| 파일 | 크기 | 용도 | 사용 |
|------|------|------|------|
| preset_storage.py | 16KB | 프리셋 저장/로드 | ★★★★★ |
| preset_manager.py | 20KB | 프리셋 관리 UI | ★★★★☆ |

### ✅ 시스템 유틸 (5개) - 필수
| 파일 | 크기 | 용도 | 사용 빈도 |
|------|------|------|----------|
| logger.py | 3.7KB | 중앙 로깅 | 매우 높음 |
| validators.py | 7.4KB | 입력 검증 | 높음 |
| retry.py | 3.9KB | 재시도 로직 | 높음 |
| crypto.py | 2.6KB | 암호화 유틸 | 중간 |
| helpers.py | 1.3KB | 범용 헬퍼 | 중간 |

### ✅ 시간 처리 (2개) - 필수
| 파일 | 크기 | 용도 | 사용 |
|------|------|------|------|
| time_utils.py | 5.3KB | 시간 변환 유틸 | ★★★★★ |
| timezone_helper.py | 9.0KB | 타임존 처리 | ★★★★★ |

### ✅ GUI/차트 (3개) - 필수
| 파일 | 크기 | 용도 | 사용 |
|------|------|------|------|
| table_models.py | 14KB | QTableWidget 모델 | ★★★★★ |
| chart_throttle.py | 6.8KB | 차트 업데이트 제한 | ★★★★☆ |
| chart_profiler.py | 7.1KB | 차트 성능 프로파일링 | ★★★☆☆ |

### ✅ 프로덕션 기능 (5개) - 유지 권장
| 파일 | 크기 | 용도 | 사용 빈도 | 비고 |
|------|------|------|----------|------|
| state_manager.py | 6.3KB | 상태 관리 | 38회 | GUI 상태 저장 |
| updater.py | 3.6KB | 자동 업데이트 | 126회 | 버전 체크 |
| health_check.py | 4.6KB | 시스템 헬스 체크 | 224회 | 거래소 연결 확인 |
| error_reporter.py | 6.7KB | 에러 리포트 | 1회 | 사용 적음 |
| api_utils.py | 5.4KB | API 유틸 | 1회 | 사용 적음 |

### ⚠️ 개발 도구 (2개) - 아카이브 고려
| 파일 | 크기 | 용도 | 사용 빈도 | 상태 |
|------|------|------|----------|------|
| optimization_impact_report.py | 16KB | 최적화 영향도 리포트 생성 | 2회 | 개발 완료 |
| new_coin_detector.py | 4.2KB | 신규 코인 감지 | 1회 | 실험적 기능 |

## 결론

### ✅ 유지 (26개) - 95%
모든 utils는 **프로덕션 기능**이거나 **자주 사용**되는 유틸리티입니다.

**핵심 이유**:
1. **SSOT 준수**: indicators, metrics, incremental_indicators (v7.14-v7.15)
2. **데이터 파이프라인**: 5개 파일 (다운로드, 캐시, 변환)
3. **프리셋 시스템**: 2개 파일 (저장/관리)
4. **시스템 안정성**: logger, validators, retry (필수)
5. **GUI 기능**: table_models, chart_throttle (PyQt6)
6. **프로덕션 운영**: state_manager, updater, health_check

### 📦 아카이브 후보 (2개) - 5%
개발 완료된 분석 도구

1. **optimization_impact_report.py** (16KB)
   - 용도: 최적화 파라미터 영향도 마크다운 리포트 생성
   - 사용: 2회 (자체 import 포함)
   - 상태: v7.18 최적화 완료 후 역할 완수
   - 판단: 아카이브 가능 (필요 시 복원)

2. **new_coin_detector.py** (4.2KB)
   - 용도: 신규 상장 코인 자동 감지
   - 사용: 1회 (자체 import)
   - 상태: 실험적 기능, 실제 활용 없음
   - 판단: 아카이브 가능

## 권장 사항

### 옵션 1: 현상 유지 (권장)
- 2개 파일(20KB)은 전체(417KB)의 4.8%에 불과
- 히스토리 가치 있음
- 복원 번거로움 없음

### 옵션 2: 선별 아카이브
```bash
# 2개만 아카이브
mkdir -p utils/archive_dev_tools_20260117
mv utils/optimization_impact_report.py utils/archive_dev_tools_20260117/
mv utils/new_coin_detector.py utils/archive_dev_tools_20260117/
```

**효과**:
- 4.8% 정리 (미미함)
- 프로덕션 명확성 소폭 향상

## 최종 판단

**utils는 정리 불필요**

이유:
1. 95% 프로덕션 활용 중
2. 아카이브 대상 2개(20KB)는 전체의 5% 미만
3. 정리 효과 미미 (tools 94%, tests 69%에 비해)
4. 유틸리티 특성상 언제든 필요할 수 있음

**결론**: **utils는 현상 유지** 권장
