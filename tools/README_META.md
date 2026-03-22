# Meta 최적화 도구 사용법

## 빠른 시작

### 1. Meta 결과로 백테스트 (가장 간단)

```bash
python tools/test_meta_result.py
```

**출력**:
```
Sharpe Ratio      : 33.01
Win Rate          : 97.7%
MDD               : 1.54%
Profit Factor     : 134.76
Total Trades      : 4457
Total PnL         : 4531.54%
```

---

### 2. 파라미터 비교

```bash
python tools/compare_meta_params.py
```

**출력**:
```
            [1] 보수적  [2] 공격적   [3] 혼합
Sharpe          33.01      26.85      31.51
Win Rate        97.7%      91.0%      96.3%
MDD             1.54%      4.59%      1.54%
PF             134.76      11.25      66.86
Trades           4457       3669       4447

최고 성능: [1]
```

---

## 도구 설명

| 파일 | 설명 | 실행 시간 |
|------|------|-----------|
| `test_meta_result.py` | Meta 최적 파라미터 1개 테스트 | 10초 |
| `compare_meta_params.py` | Meta 파라미터 3개 비교 | 30초 |
| `simple_meta_backtest.py` | 상세 출력 버전 (2개 조합) | 20초 |
| `run_backtest_from_meta.py` | 전체 조합 테스트 (수정 필요) | - |

---

## Meta 최적화란?

**자동으로 최적 파라미터 범위를 찾는 시스템**

```
14,700개 조합 (전체)
    ↓ 랜덤 샘플링 200개
    ↓ 백테스트
    ↓ 상위 10% 추출
    ↓ 범위 재탐색
    ↓
Quick: 2개 값 [0.5, 1.28]  ← 빠른 검증
Deep:  5개 값 [0.5, 0.69, 0.89, 1.08, 1.28]  ← 정밀 탐색
```

**소요 시간**: 20초 (400개 조합)

---

## Meta 결과 파일

**위치**: `presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json`

**구조**:
```json
{
  "param_ranges_by_mode": {
    "atr_mult": {
      "quick": [0.5, 1.28],
      "deep": [0.5, 0.69, 0.89, 1.08, 1.28]
    },
    "filter_tf": {
      "quick": ["2h", "4h"]
    }
  }
}
```

---

## 최적 파라미터 (2026-01-17 검증)

```python
best_params = {
    'atr_mult': 0.5,              # 타이트 손절
    'filter_tf': '2h',            # 짧은 필터
    'trail_start_r': 0.5,         # 빠른 익절
    'trail_dist_r': 0.015,        # 1.5% 익절
    'entry_validity_hours': 12.0  # 빠른 진입
}
```

**성능**:
- Sharpe: 33.01
- 승률: 97.7%
- MDD: 1.54%

---

## 추가 문서

- 상세 가이드: [docs/META_OPTIMIZATION_USAGE.md](../docs/META_OPTIMIZATION_USAGE.md)
- CLAUDE.md: 시스템 아키텍처
