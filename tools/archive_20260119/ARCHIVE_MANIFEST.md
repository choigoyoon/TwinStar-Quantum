# Archive 2026-01-19 - Project Cleanup

## 아카이브 개요

**일자**: 2026-01-19
**버전**: v7.25 (백테스트 수익률 표준 정립)
**목적**: v7.25 완료 후 프로젝트 정리 (루트 디렉토리 임시 파일 제거)

## 아카이브 통계

- **진단 스크립트**: 80+ 파일
- **결과 파일**: 7개 (텍스트, CSV, 배치)
- **문서**: 15+ 파일 (분석 리포트, 작업 로그)
- **총 크기**: ~2MB

## 디렉토리 구조

```
archive_20260119/
├── diagnostics/           # 진단 및 분석 스크립트 (80+개)
│   ├── analyze_*.py
│   ├── check_*.py
│   ├── compare_*.py
│   ├── debug_*.py
│   ├── test_*.py
│   └── ...
├── results/               # 실행 결과 (7개)
│   ├── adaptive_result.txt
│   ├── adaptive_result_v2.txt
│   ├── entry_ohl_analysis.csv
│   ├── ohl_distribution_result.txt
│   ├── sensitivity_result.txt
│   ├── signal_results.txt
│   └── run_fill_rate.bat
└── temp_scripts/          # 임시 스크립트 (12개)
    ├── analyze_ohl.py
    ├── calculate_fill_rate.py
    ├── check_data.py
    ├── check_low_distribution.py
    ├── check_ohl_distribution.py
    ├── fill_rate_0001.py
    ├── fill_rate_summary.md
    ├── quick_fill_rate.py
    ├── simple_count.py
    ├── test_grid_meta.py
    ├── test_tf_validation.py
    └── test_v722_integration.py
```

## 주요 아카이브 파일

### 진단 스크립트

**분석 도구** (analyze_*.py):
- `analyze_actual_entry_candles.py` - 실제 진입 캔들 분석
- `analyze_entry_oc_gap.py` - 진입 OC 갭 분석
- `analyze_high_winrate.py` - 고승률 분석
- `analyze_low_drop.py` - 낮은 하락 분석
- `analyze_mdd_tradeoff.py` - MDD 트레이드오프 분석
- `analyze_meta_bottleneck.py` - 메타 최적화 병목 분석
- `analyze_websocket_vs_backtest.py` - WebSocket vs 백테스트 비교

**검증 도구** (check_*.py):
- `check_data_rows.py` - 데이터 행 수 확인
- `check_preset_versions.py` - 프리셋 버전 확인
- `check_signal_ohlcv.py` - 신호 OHLCV 확인
- `check_zero_slippage.py` - 슬리피지 0 확인

**비교 도구** (compare_*.py):
- `compare_macd_adx.py` - MACD vs ADX 비교
- `compare_market_limit.py` - 시장가 vs 지정가 비교
- `compare_old_vs_new.py` - 구버전 vs 신버전 비교

**디버깅 도구** (debug_*.py):
- `debug_coarse_worker.py` - Coarse 워커 디버그
- `debug_entry_price_diff.py` - 진입가 차이 디버그
- `debug_fill_rate.py` - 체결률 디버그

**테스트 스크립트** (test_*.py):
- `test_adaptive_range.py` - 적응형 범위 테스트
- `test_adx_*.py` - ADX 관련 테스트 (5개)
- `test_exchange_optimization.py` - 거래소 최적화 테스트
- `test_fine_tuning*.py` - Fine-Tuning 테스트 (3개)
- `test_limit_order_*.py` - 지정가 주문 테스트 (2개)
- `test_optimal_params.py` - 최적 파라미터 테스트
- `test_phase1_quick.py` - Phase 1 빠른 테스트
- `test_scoring_methods.py` - 점수 계산 방법 테스트
- `test_sensitivity_analysis.py` - 민감도 분석 테스트
- `test_v722_integration.py` - v7.22 통합 테스트

**기타 도구**:
- `adaptive_range_builder.py` - 적응형 범위 빌더
- `backtest_with_limit_order.py` - 지정가 백테스트
- `btc_based_compound_strategy.py` - BTC 기반 복리 전략
- `calculate_compound_leverage.py` - 복리 레버리지 계산
- `calculate_leverage_performance.py` - 레버리지 성능 계산
- `calculate_trade_frequency.py` - 거래 빈도 계산
- `exchange_distribution_strategy.py` - 거래소 분산 전략
- `multi_symbol_backtest.py` - 멀티 심볼 백테스트
- `optimal_entry_analysis.py` - 최적 진입 분석
- `optimize_params.py` - 파라미터 최적화
- `profile_meta_optimization.py` - 메타 최적화 프로파일링
- `quick_*.py` - 빠른 검증 스크립트 (6개)
- `realistic_compound_strategy.py` - 현실적 복리 전략
- `revalidate_all_presets.py` - 모든 프리셋 재검증
- `save_optimal_preset.py` - 최적 프리셋 저장
- `simple_*.py` - 단순 테스트 스크립트 (2개)
- `simulate_limit_order_performance.py` - 지정가 성능 시뮬레이션
- `verify_phase1_result.py` - Phase 1 결과 검증
- `verify_preset_entry_distribution.py` - 프리셋 진입 분포 검증
- `walk_forward_validation.py` - Walk-Forward 검증

### 결과 파일

1. **adaptive_result.txt** (20KB)
   - 적응형 범위 추출 결과 (초기 버전)

2. **adaptive_result_v2.txt** (20KB)
   - 적응형 범위 추출 결과 (개선 버전)

3. **entry_ohl_analysis.csv** (606KB)
   - 진입 캔들 OHLC 분석 데이터
   - 10,133개 거래 OC 갭 분포

4. **ohl_distribution_result.txt** (1.5KB)
   - OHL 분포 분석 결과

5. **sensitivity_result.txt** (448B)
   - 민감도 분석 결과

6. **signal_results.txt** (261KB)
   - 신호 검증 결과

7. **run_fill_rate.bat** (139B)
   - 체결률 계산 배치 파일

### 임시 스크립트

1. **analyze_ohl.py** - OHL 분석
2. **calculate_fill_rate.py** - 체결률 계산
3. **check_data.py** - 데이터 확인
4. **check_low_distribution.py** - 낮은 분포 확인
5. **check_ohl_distribution.py** - OHL 분포 확인
6. **fill_rate_0001.py** - 체결률 계산 (버전 0001)
7. **fill_rate_summary.md** - 체결률 요약
8. **quick_fill_rate.py** - 빠른 체결률 계산
9. **simple_count.py** - 단순 카운트
10. **test_grid_meta.py** - 그리드 메타 테스트
11. **test_tf_validation.py** - 타임프레임 검증 테스트
12. **test_v722_integration.py** - v7.22 통합 테스트

## 복원 방법

개별 파일 복원:
```bash
cp tools/archive_20260119/{category}/{filename} ./
```

전체 롤백:
```bash
git revert {commit_hash}
```

## 프로덕션 필수 파일 (유지)

루트 디렉토리:
1. `run_gui.py` - GUI 진입점
2. `CLAUDE.md` - 프로젝트 규칙 (v7.25)
3. `README.md` - 프로젝트 개요
4. `requirements.txt` - 의존성
5. `STRATEGY_GUIDE.md` - 사용자 문서
6. `LICENSE.txt` - 라이선스
7. `.gitignore` - Git 설정
8. `pyrightconfig.json` - 타입 체커
9. `version.json` - 버전 정보
10. `license_manager.py`, `license_tiers.py` - 라이선스 시스템
11. `telegram_notifier.py`, `paths.py` - 지원 모듈

tools/ 디렉토리:
- `verify_preset_backtest.py` - 프리셋 백테스트 검증 (신규)
- `test_fine_tuning_integration.py` - Fine-Tuning 통합 테스트
- `test_fine_tuning_quick.py` - Fine-Tuning 빠른 테스트

## 아카이브 이유

### v7.25 완료 작업
- 백테스트 수익률 표준 정립 (6가지 핵심 지표)
- 타임프레임 계층 검증 시스템 구축
- ADX 필터 불필요 확인
- Phase 1 Fine-Tuning 완료 (Sharpe 27.32, 승률 95.7%)

### 정리 목적
1. **루트 디렉토리 클린업**: 임시 스크립트 제거
2. **프로덕션 준비**: 필수 파일만 유지
3. **히스토리 보존**: 분석 과정 아카이브

## 관련 커밋

- v7.25.1: 타임프레임 계층 검증 + ADX 테스트
- v7.25: 백테스트 수익률 표준 정립
- v7.24: 백테스트 메트릭 불일치 해결

## 참고 문서

프로젝트 루트:
- `CLAUDE.md` - 개발 규칙 (v7.25)
- `docs/PRESET_STANDARD_v724.md` - 프리셋 표준
- `docs/archive_20260119/` - 분석 리포트 및 작업 로그

---

**작성일**: 2026-01-19
**작성자**: Claude Sonnet 4.5
