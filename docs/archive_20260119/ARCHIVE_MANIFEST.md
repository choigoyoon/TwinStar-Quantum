# Docs Archive 2026-01-19

## 아카이브 개요

**일자**: 2026-01-19
**버전**: v7.25
**목적**: 분석 리포트 및 작업 로그 아카이브

## 디렉토리 구조

```
archive_20260119/
├── analysis_reports/      # 분석 리포트 (15개)
│   ├── ADX_*.md
│   ├── LIMIT_ORDER_*.md
│   ├── WM_*.md
│   ├── COARSE_*.md
│   ├── META_*.md
│   ├── OPTIMIZATION_*.md
│   └── 플랜_*.md, 최적_*.md, 타임프레임_*.md (한글)
│
└── work_logs/             # 작업 로그 (3개)
    ├── WORK_LOG_20260117.txt
    ├── WORK_LOG_20260117_V722_VALIDATION.txt
    └── WORK_LOG_20260118.txt
```

## 분석 리포트

### ADX 관련 (3개)

1. **ADX_PERFORMANCE_ANALYSIS.md**
   - ADX 필터 성능 분석
   - 임계값별 성능 비교

2. **ADX_STRATEGY_COMPARISON.md**
   - MACD vs ADX-DI 전략 비교
   - 승률, MDD, Profit Factor 비교

3. **ADX_STRATEGY_DIAGNOSIS.md**
   - ADX 전략 진단
   - 문제점 및 개선 방향

### 지정가 주문 관련 (3개)

4. **LIMIT_ORDER_ANALYSIS_20260118.md**
   - 지정가 주문 분석 (2026-01-18)
   - 체결률, 슬리피지 분석

5. **LIMIT_ORDER_FINAL_SUMMARY_20260119.md**
   - 지정가 주문 최종 요약 (2026-01-19)
   - 결론: 시장가 주문 권장

6. **LIMIT_ORDER_VARIANCE_REDUCTION_20260119.md**
   - 지정가 주문 변동성 감소 분석
   - OC 갭 분포 분석

### 성능 분석 (1개)

7. **WM_HIGH_PERFORMANCE_ANALYSIS_20260119.md**
   - W/M 패턴 고성능 분석 (2026-01-19)
   - 승률 95.7%, Sharpe 27.32 달성

### 최적화 관련 (4개)

8. **COARSE_TO_FINE_OPTIMIZATION_REPORT_20260118.md**
   - Coarse-to-Fine 최적화 리포트
   - Phase 1 결과 (2026-01-18)

9. **META_RESULT_ANALYSIS.md**
   - 메타 최적화 결과 분석
   - 범위 추출 검증

10. **OPTIMIZATION_RESULTS_20260118.md**
    - 최적화 결과 (2026-01-18)
    - 파라미터별 성능 비교

11. **BACKTEST_METRIC_DISCREPANCY_REPORT.md** (유지 - 루트 docs/)
    - 백테스트 메트릭 불일치 리포트
    - v7.24 Phase 1-D 관련

### 한글 계획서 (4개)

12. **플랜_메트릭_재현성_20260117.md**
    - 메트릭 재현성 개선 계획

13. **플랜_백테스트_개념_재정립_20260118.md**
    - 백테스트 개념 재정립 계획
    - v7.25 백테스트 수익률 표준

14. **최적_파라미터_도출_과정_20260118.md**
    - 최적 파라미터 도출 과정
    - Fine-Tuning 프로세스

15. **타임프레임_계층_검증_20260118.md**
    - 타임프레임 계층 검증
    - 자동 검증 시스템

16. **타임프레임_계층_검증_ADX_테스트_20260118.md**
    - 타임프레임 계층 검증 + ADX 테스트
    - v7.25.1 관련

## 작업 로그

### 2026-01-17

1. **WORK_LOG_20260117.txt**
   - v7.20 메타 최적화 시스템 완성
   - v7.23 AI 작업 효율성 가이드

2. **WORK_LOG_20260117_V722_VALIDATION.txt**
   - v7.22 검증 작업
   - GUI 최적화 완료

### 2026-01-18

3. **WORK_LOG_20260118.txt**
   - v7.25 백테스트 수익률 표준
   - Fine-Tuning 최적화 완료

## 유지 문서 (루트 docs/)

### 프로덕션 필수

1. **PRESET_STANDARD_v724.md**
   - 프리셋 표준 (v7.24)
   - 파일명, JSON 구조, 표기값 표준

2. **META_OPTIMIZATION_PERFORMANCE_ANALYSIS.md**
   - 메타 최적화 성능 분석
   - 랜덤 샘플링 + 백분위수 기반

3. **BACKTEST_METRIC_DISCREPANCY_REPORT.md**
   - 백테스트 메트릭 불일치 리포트
   - v7.24 Phase 1-D

### 사용자 문서 (루트)

- `README.md` - 프로젝트 개요
- `STRATEGY_GUIDE.md` - 전략 가이드
- `CLAUDE.md` - 개발 규칙 (v7.25)

## 복원 방법

```bash
# 개별 파일 복원
cp docs/archive_20260119/{category}/{filename} docs/

# 전체 복원
cp -r docs/archive_20260119/analysis_reports/* docs/
cp -r docs/archive_20260119/work_logs/* docs/
```

## 아카이브 이유

1. **프로덕션 준비**: 루트 docs/ 정리
2. **히스토리 보존**: 분석 과정 기록
3. **참조 용이성**: 카테고리별 분류

---

**작성일**: 2026-01-19
**작성자**: Claude Sonnet 4.5
