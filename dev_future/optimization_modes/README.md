# 최적화 모드 개발 대기 (Future Development)

## 📁 개요

**Fine-Tuning 모드**가 최고 성능을 보여 기본값으로 채택되었습니다.
나머지 최적화 모드들은 향후 개발 및 실험용으로 이 폴더에 보관합니다.

## 🎯 성능 비교

### Fine-Tuning (v7.25) - **현재 기본값** ✅
- **Sharpe**: 27.32
- **승률**: 95.7%
- **MDD**: 0.8%
- **PnL**: 826.8%
- **Profit Factor**: 26.68 (S등급)
- **조합**: 108개 (유효 조합, TF 검증 통과)
- **시간**: ~72초

### Meta (실험적)
- 자동 범위 탐색
- ~3,000개 조합
- 20초 소요
- 성능: Fine-Tuning 대비 낮음

### Quick (테스트용)
- 빠른 검증용
- ~8개 조합만
- 2분 소요
- 성능: 검증용으로만 사용

### Deep (시간 소모)
- 세부 최적화
- ~1,080개 조합
- 4-5시간 소요
- 성능: 시간 대비 효율 낮음

## 📦 이동된 파일

### Meta 최적화 관련
1. **meta_worker.py** (248줄)
   - MetaOptimizationWorker QThread 클래스
   - 백그라운드 메타 최적화 실행

2. **meta_ranges.py** (120줄)
   - META_PARAM_RANGES 정의
   - 14,700개 조합 범위

3. **meta_optimizer.py** (~400줄)
   - MetaOptimizer 클래스
   - 랜덤 샘플링 + 백분위수 기반 범위 추출

### 연결 끊김 필요
- `ui/widgets/optimization/single_business_mixin.py`: `_run_meta_optimization()` 메서드
- `ui/widgets/optimization/single.py`: MODE_MAP에서 meta 제거
- `CLAUDE.md`: 메타 최적화 섹션 마이그레이션 표시

## 🔧 재활성화 방법

향후 Meta 최적화를 다시 사용하려면:

1. 파일 복원
```bash
git mv dev_future/optimization_modes/meta_*.py config/
git mv dev_future/optimization_modes/meta_optimizer.py core/
git mv dev_future/optimization_modes/meta_worker.py ui/widgets/optimization/
```

2. UI 연결 복원
- `single.py`: MODE_MAP에 meta 재추가
- `single_business_mixin.py`: `_run_meta_optimization()` 주석 해제

3. Import 경로 수정
```python
from config.meta_ranges import META_PARAM_RANGES
from core.meta_optimizer import MetaOptimizer
from ui.widgets.optimization.meta_worker import MetaOptimizationWorker
```

## 📊 Quick/Deep 모드

**Quick/Deep 모드는 여전히 활성화 상태입니다.**
- `core/optimizer.py`: `generate_quick_grid()`, `generate_deep_grid()` 메서드
- `ui/widgets/optimization/single.py`: MODE_MAP에 quick(2), deep(3) 유지

**이유**:
- Quick: 빠른 검증용으로 유용
- Deep: 선택적 세부 최적화 가능

## 🎯 권장 사항

**실전 매매**: Fine-Tuning만 사용 (기본값)
**실험/연구**: Meta, Quick, Deep 필요 시 재활성화

## 📝 관련 문서

- `docs/플랜_메타최적화_20260117.md`: Meta 최적화 구현 계획서
- `CLAUDE.md`: "🔍 메타 최적화 (Meta-Optimization) - v7.20" 섹션

---

**마이그레이션 일자**: 2026-01-20
**이유**: Fine-Tuning이 최고 성능 (Sharpe 27.32, 승률 95.7%)
