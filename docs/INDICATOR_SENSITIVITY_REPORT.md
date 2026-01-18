# 지표 민감도 분석 리포트

분석 일시: 2026-01-15 13:03:51.854097
분석 대상: bybit BTCUSDT
분석 시간: 1.2분

## 민감도 요약

| 파라미터 | 종합 점수 | 권장사항 | 최적값 |
|---------|----------|---------|--------|
| macd_fast | 0.000 | LOW | 5 |
| macd_slow | 0.000 | LOW | 16 |
| adx_period | 0.000 | LOW | 8 |
| adx_threshold | 0.000 | LOW | 18 |
| atr_mult | 0.000 | LOW | 0.8 |
| rsi_period | 0.000 | LOW | 5 |

## 모드별 권장 범위


### QUICK 모드

```python
QUICK_RANGE = {
    'macd_fast': [5],
    'macd_slow': [16],
    'adx_period': [8],
    'adx_threshold': [18],
    'atr_mult': [0.8],
    'rsi_period': [5],
}
```

### STANDARD 모드

```python
STANDARD_RANGE = {
    'macd_fast': [5],
    'macd_slow': [16],
    'adx_period': [8],
    'adx_threshold': [18],
    'atr_mult': [0.8],
    'rsi_period': [5],
}
```

### DEEP 모드

```python
DEEP_RANGE = {
    'macd_fast': [5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
    'macd_slow': [16, 18, 20, 22, 24, 26, 28, 30, 32, 34],
    'adx_period': [8, 10, 12, 14, 16, 18, 20, 25, 30],
    'adx_threshold': [15, 18, 20, 22, 25, 28, 30, 35],
    'atr_mult': [0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0],
    'rsi_period': [5, 7, 9, 11, 14, 17, 21, 25, 30],
}
```
