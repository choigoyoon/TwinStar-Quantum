# Archive Manifest - 2026-01-16

## 목적 (Purpose)

v7.18 최적화 시스템 완료 후 프로덕션 준비를 위한 루트 디렉토리 정리.
프로젝트 구조 개선 및 불필요한 진단/테스트 파일 아카이브.

## 아카이브 일시 (Archive Date)

**2026-01-16 23:40 UTC+9 (KST)**

---

## 아카이브 통계 (Statistics)

| 항목 | 수량 | 크기 |
|------|------|------|
| 총 파일 수 | 160+ | ~17MB |
| 진단 스크립트 | 49 | ~6.5MB |
| 최적화 결과 (CSV) | 11 | ~500KB |
| 문서 (MD) | 44 | ~2MB |
| 로그 (TXT) | 34 | ~1MB |
| 레거시 디렉토리 | 4 | ~16.3MB |
| Pip 아티팩트 (삭제) | 22 | - |

---

## 내용 (Contents)

### 1. diagnostics/ (49개 파일)

**진단 및 분석 스크립트** - 프로젝트 개발 중 사용한 일회성 도구

| 파일 | 용도 |
|------|------|
| analyze_gui_tree.py | GUI 의존성 분석 |
| analyze_pyright.py | Pyright 에러 분석 (1.7K줄) |
| check_env.py | 환경 검사 (1.5K줄) |
| cleanup_project.py | 프로젝트 정리 유틸 (2.7K줄) |
| compare_live_bt.py | 실시간 vs 백테스트 비교 (2.8K줄) |
| core_quality_scanner.py | Core 코드 품질 검사 (2.4K줄) |
| exchanges_quality_scanner.py | 거래소 코드 품질 (1.6K줄) |
| gui_quality_scanner.py | GUI 코드 품질 (1.9K줄) |
| system_doctor.py | 시스템 진단 (2.2K줄) |
| ... | (40개 더) |

### 2. results/ (11개 CSV)

**최적화 결과 데이터** - 파라미터 최적화 실험 결과

| 파일 | 테스트 항목 |
|------|------------|
| atr_mult_test_results_20260116_160325.csv | ATR 배수 최적화 |
| filter_tf_hypothesis_results_*.csv | 필터 타임프레임 가설 검증 (5개) |
| final_combination_results_20260116_173131.csv | 최종 조합 테스트 |
| leverage_optimization_results_20260116_173019.csv | 레버리지 최적화 |
| trail_optimization_results_*.csv | 트레일링 익절 최적화 (3개) |

### 3. docs/ (44개 MD)

**프로젝트 문서 및 리포트** - 개발 과정 기록

| 파일 | 내용 |
|------|------|
| COMPREHENSIVE_OPTIMIZATION_REPORT.md | 종합 최적화 리포트 |
| FINAL_OPTIMIZATION_RESULT.md | 최종 최적화 결과 |
| FINAL_SUMMARY.md | 최종 요약 |
| MERGE_CHECKLIST.md | 병합 체크리스트 |
| OPTIMIZATION_FINAL_SUMMARY_20260116.md | 최적화 최종 요약 |
| OPTIMIZATION_MODES_GUIDE.md | 최적화 모드 가이드 |
| STRATEGY_IMPROVEMENT_PLAN.md | 전략 개선 계획 |
| WINNING_RATE_PARADOX.md | 승률 역설 분석 |
| WIN_RATE_80_STRATEGY.md | 80% 승률 전략 |
| PR_DESCRIPTION.md | PR 설명 |
| ... | (34개 더) |

### 4. logs/ (34개 TXT)

**작업 로그 파일** - 개발 일지 및 실행 로그

| 파일 | 내용 |
|------|------|
| docs/WORK_LOG_*.txt | 일별 작업 로그 (docs/ 하위 15개) |
| trail_optimization_log.txt | 트레일링 최적화 로그 |
| result_output.txt | 결과 출력 |
| all_py_files.txt | 전체 Python 파일 목록 |
| build_log.txt | 빌드 로그 |
| ... | (30개 더) |

### 5. legacy/ (4개 디렉토리, 16.3MB)

**레거시 코드** - 현재 프로덕션 코드로 대체됨

| 디렉토리 | 대체 버전 | 크기 |
|---------|-----------|------|
| backups/ | core/unified_bot.py (v7.16) | 255KB |
| refactor_backup/ | core/optimizer.py, core/strategy_core.py (v7.18) | 350KB |
| for_local/ | (실험적 전략, 미사용) | 50KB |
| sandbox_optimization/ | (대안 프레임워크, 미사용) | 100KB |
| tools/archive_scripts/ | (90+ 진단 스크립트, 히스토리) | 15MB |
| tools/archive_temp/ | (임시 백업 파일) | 500KB |

---

## 복원 방법 (Restore)

### 개별 파일 복원

```bash
# 진단 스크립트
git mv tools/archive_20260116/diagnostics/{filename} ./

# 최적화 결과
git mv tools/archive_20260116/results/{filename} ./

# 문서
git mv tools/archive_20260116/docs/{filename} ./

# 로그
git mv tools/archive_20260116/logs/{filename} ./

# 레거시 디렉토리
git mv tools/archive_20260116/legacy/{dirname} ./
```

### 전체 복원 (롤백)

```bash
# Git 커밋 되돌리기
git revert {commit_hash}

# 또는 강제 리셋 (주의!)
git reset --hard HEAD~1
```

---

## 프로덕션 필수 파일 (유지)

루트 디렉토리에 남은 **8개 필수 파일**:

1. **run_gui.py** - GUI 진입점
2. **CLAUDE.md** - 프로젝트 규칙 (v7.18)
3. **README.md** - 프로젝트 개요
4. **requirements.txt** - 의존성 목록
5. **STRATEGY_GUIDE.md** - 사용자 문서
6. **LICENSE.txt** - 라이선스
7. **.gitignore** - Git 설정
8. **.env.example** - 환경 변수 템플릿

---

## 검증 완료 (Verification)

프로덕션 검증 스크립트: `tools/verify_production_ready.py`

**결과**: 6/6 항목 통과 (2026-01-16)
1. ✓ Entry Points
2. ✓ Import Integrity (18개 모듈)
3. ✓ Config Files (10개)
4. ✓ Storage Init
5. ✓ SSOT Compliance (v7.15-v7.18)
6. ✓ GUI Launch (PyQt6)

---

## 아카이브 이유 (Rationale)

1. **개발 완료**: v7.18 최적화 시스템 완성
2. **코드 정리**: 프로덕션 준비 단계
3. **유지보수**: 불필요한 파일 제거로 프로젝트 가독성 향상
4. **히스토리 보존**: git mv로 모든 변경 이력 유지

---

## 관련 커밋 (Related Commits)

**커밋 메시지**: `chore: 프로덕션 준비 - 루트 디렉토리 정리 (v7.18)`

**주요 변경**:
- 루트 95% 감소 (160+ → 8개)
- 아카이브 생성 (tools/archive_20260116/)
- 검증 스크립트 추가 (tools/verify_production_ready.py)
- CLAUDE.md 업데이트 (아카이브 섹션 추가)

---

## 작성자 (Author)

- **Claude Sonnet 4.5** <noreply@anthropic.com>
- **작성일**: 2026-01-16
- **버전**: TwinStar-Quantum v7.18

---

## 라이선스 (License)

이 아카이브는 TwinStar-Quantum 프로젝트와 동일한 라이선스를 따릅니다.
