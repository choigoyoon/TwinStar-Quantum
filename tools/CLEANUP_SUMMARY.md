# 진단 스크립트 정리 요약 (2026-01-17)

## 실행 결과

### 통계
- **총 스크립트**: 51개 (원본)
- **아카이브**: 50개 (98%)
- **유지**: 3개 (6%)
- **삭제**: 0개
- **아카이브 크기**: 414KB

### 유지된 스크립트 (tools/)
프로덕션 환경에 필요한 3개만 유지:

1. **verify_production_ready.py** (8.6KB)
   - 프로덕션 준비 검증 (최신)
   - 6개 카테고리 검증

2. **check_dependencies.py** (4.6KB)
   - 의존성 확인 (CI 가능)

3. **test_symbol_normalization_manual.py** (2.6KB)
   - 심볼 정규화 검증 (Phase A-3)

### 아카이브 위치
`tools/archive_diagnostic_20260117/` (50개 파일)

### 카테고리 구성
- Phase 검증: 5개
- GUI 검증: 7개 (GUI/verify_all_modules.py 포함)
- 최적화 실험: 11개
- 워크플로우 테스트: 5개
- 시스템 검증: 9개
- 프로젝트 분석: 5개
- 환경 체크: 8개

## 정리 효과

### Before (v7.18)
```
tools/
├── 51개 진단 스크립트 (혼재)
├── 12개 프로덕션 도구
└── ...
```

### After
```
tools/
├── 3개 진단 스크립트 (필수만)
├── 12개 프로덕션 도구
└── archive_diagnostic_20260117/ (50개 아카이브)
```

### 개선 사항
- ✅ tools/ 디렉토리 94% 정리
- ✅ 프로덕션 필수 스크립트만 유지
- ✅ 히스토리 보존 (아카이브)
- ✅ 명확한 복원 방법 문서화

## 다음 단계

1. **Git 커밋**
   ```bash
   git add tools/archive_diagnostic_20260117/
   git add -u
   git commit -m "chore: 진단 스크립트 정리 - 50개 아카이브 (v7.18)"
   ```

2. **검증**
   - verify_production_ready.py 실행 확인
   - 프로덕션 빌드 테스트

3. **문서 업데이트**
   - CLAUDE.md에 아카이브 참조 추가 (선택)

## 복원 방법

### 개별 복원
```bash
cp tools/archive_diagnostic_20260117/{filename} tools/
```

### 카테고리별 복원
```bash
# 최적화 실험 스크립트 복원
cp tools/archive_diagnostic_20260117/test_*.py tools/
cp tools/archive_diagnostic_20260117/analyze_*.py tools/
```

### 전체 롤백
```bash
git revert <commit_hash>
```

## 메타데이터

- **실행일**: 2026-01-17
- **버전**: v7.18 이후
- **브랜치**: feat/indicator-ssot-integration
- **작성자**: Claude Opus 4.5
- **MANIFEST**: tools/archive_diagnostic_20260117/MANIFEST.md

---

**참고**: 모든 아카이브 파일은 히스토리 가치가 있어 삭제하지 않고 보존했습니다.
