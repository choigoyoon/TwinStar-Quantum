# 🚀 TwinStar-Quantum 실전 운영 가이드

> **버전**: v1.0
> **작성일**: 2026-01-14
> **대상**: 실전 트레이더, 시스템 운영자

---

## 📋 목차

1. [시스템 개요](#1-시스템-개요)
2. [수수료 구조 검증](#2-수수료-구조-검증)
3. [데이터 흐름](#3-데이터-흐름)
4. [백테스트 실행](#4-백테스트-실행)
5. [파라미터 최적화](#5-파라미터-최적화)
6. [실매매 운영](#6-실매매-운영)
7. [문제 해결](#7-문제-해결)
8. [안전 수칙](#8-안전-수칙)

---

## 1. 시스템 개요

### 1.1 프로젝트 구조

TwinStar-Quantum은 **암호화폐 자동매매 플랫폼**으로, CCXT 기반 다중 거래소를 지원합니다.

```
핵심 원칙:
✅ 백테스트 = 실매매 (동일 로직)
✅ Single Source of Truth (15분봉 원본)
✅ Radical Delegation (모듈 분리)
✅ Deterministic (결정적 결과)
```

### 1.2 지원 거래소

| 거래소 | 선물 | 현물 | WebSocket | 비고 |
|--------|------|------|-----------|------|
| Bybit | ✅ | ❌ | ✅ | 권장 (안정성) |
| Binance | ✅ | ✅ | ✅ | 높은 유동성 |
| OKX | ✅ | ❌ | ❌ | |
| Bitget | ✅ | ❌ | ❌ | |
| BingX | ✅ | ❌ | ❌ | |
| Upbit | ❌ | ✅ | ❌ | 한국 거래소 |
| Bithumb | ❌ | ✅ | ❌ | 한국 거래소 |
| Lighter | ✅ | ❌ | ❌ | |

### 1.3 전략 개요

**AlphaX7 Core 전략:**
- W/M 패턴 탐지 (L-H-L, H-L-H)
- MACD 기반 H/L 포인트 추출
- MTF (Multi-Timeframe) 필터
- 적응형 트레일링 스톱
- RSI 기반 진입/청산

---

## 2. 수수료 구조 검증

### 2.1 현재 설정값

**파일: `config/constants/trading.py`**

```python
SLIPPAGE = 0.0006       # 슬리피지 (0.06%)
FEE = 0.00055           # 거래 수수료 (0.055%)
TOTAL_COST = 0.00115    # 편도 총 비용 (0.115%)
```

### 2.2 왕복 비용 계산

```
편도 비용 = 0.0006 + 0.00055 = 0.00115 (0.115%)
왕복 비용 = 0.00115 × 2 = 0.0023 (0.23%)
```

**✅ 검증 결과: 왕복 0.23% 일치**

### 2.3 손익분기점

```python
# 손익분기 가격 변동률
breakeven_move = (FEE + SLIPPAGE) × 2 = 0.23%

# 예시: BTC 40,000 USDT 진입
breakeven_price = 40,000 × (1 + 0.0023) = 40,092 USDT
```

**레버리지 10배 기준:**
- 가격이 0.23% 상승 시 → 손익 ±0% (손익분기)
- 가격이 1% 상승 시 → 수익 +9.77% (10% - 0.23%)
- 가격이 2% 상승 시 → 수익 +19.77%

### 2.4 손익 계산 예시

**예시 1: Long 포지션 (+5% 수익)**

```
진입: $40,000
청산: $42,000 (+5%)
크기: $1,000
레버리지: 10x

원시 손익 = (42,000 - 40,000) / 40,000 × 1,000 × 10 = $500
수수료 = 1,000 × 0.00115 × 2 = $2.30
순손익 = $500 - $2.30 = $497.70
수익률 = 49.77%
```

**예시 2: Short 포지션 (-3% 손실)**

```
진입: $40,000
청산: $41,200 (+3% 가격 상승)
크기: $1,000
레버리지: 10x

원시 손익 = (40,000 - 41,200) / 40,000 × 1,000 × 10 = -$300
수수료 = $2.30
순손익 = -$300 - $2.30 = -$302.30
손실률 = -30.23%
```

### 2.5 검증 스크립트 실행

**간단 검증:**

```bash
cd f:\TwinStar-Quantum
./venv/Scripts/python.exe tools/simple_verification.py
```

**전체 백테스트 검증:**

```bash
./venv/Scripts/python.exe tools/full_backtest_verification.py
```

---

## 3. 데이터 흐름

### 3.1 데이터 소스

**1. CCXT REST API (과거 데이터)**

```python
from exchanges.bybit_exchange import BybitExchange

exchange = BybitExchange(api_key, secret)
klines = exchange.get_klines(
    symbol='BTCUSDT',
    timeframe='15m',
    limit=1000
)
```

**2. WebSocket (실시간 스트림)**

```python
# 자동 연결 (UnifiedBot 시작 시)
# 15분봉 클로즈 이벤트 수신
# 가격 업데이트 실시간 수신
```

**3. Parquet 캐시 (로컬 저장소)**

```
data/cache/
├── bybit_btcusdt_15m.parquet   # 15분봉 원본 (최대 1000개)
└── bybit_btcusdt_1h.parquet    # 1시간봉 (리샘플링)
```

### 3.2 데이터 처리 파이프라인

```
[거래소 REST API]
       ↓
[BotDataManager]
    ↓        ↓
15m 원본   리샘플링 (1h)
    ↓        ↓
[IndicatorGenerator]
    ↓        ↓
RSI/ATR/MACD 추가
    ↓        ↓
[AlphaX7Core]
    ↓
W/M 패턴 탐지 + MTF 필터
    ↓
[run_backtest() / UnifiedBot]
    ↓
거래 결과 (trades)
```

### 3.3 Single Source of Truth (SSOT)

**핵심 원칙:**
- **15분봉만 저장** (단일 소스)
- 1시간봉, 4시간봉은 15분봉 리샘플링으로 생성
- 모든 타임프레임이 일관성 보장

```python
# 15분봉 로드
df_15m = dm.load_historical(timeframe='15m')

# 1시간봉 자동 생성
df_1h = dm.df_entry_resampled  # 리샘플링됨

# 4시간봉 자동 생성
df_4h = dm.df_filter_full      # 리샘플링됨
```

### 3.4 캐시 관리

**자동 업데이트:**
- 봇 실행 시 5분마다 갭 보충
- WebSocket으로 실시간 업데이트

**수동 업데이트:**

```bash
# GUI: 설정 탭 → 캐시 관리 → "업데이트"
```

**캐시 초기화:**

```bash
# 수동 삭제
rm -rf data/cache/*

# GUI: 설정 탭 → 캐시 관리 → "초기화"
```

---

## 4. 백테스트 실행

### 4.1 GUI 방식 (권장)

**1. GUI 실행**

```bash
cd f:\TwinStar-Quantum
./venv/Scripts/python.exe run_gui.py
```

**2. 백테스트 탭 선택**

![Backtest Tab](docs/images/backtest_tab.png)

**3. 설정**

- 거래소: Bybit
- 심볼: BTCUSDT
- 타임프레임: 15m (Entry), 1h (Pattern)
- 프리셋: Default 또는 최적화 결과 로드

**4. 실행**

- "실행" 버튼 클릭
- 진행률 표시 (1000 캔들 기준 ~5초)

**5. 결과 확인**

| 지표 | 설명 |
|------|------|
| 승률 | 전체 거래 중 수익 거래 비율 |
| MDD | Maximum Drawdown (최대 낙폭) |
| 샤프비율 | 위험 대비 수익률 |
| 총 수익률 | 초기 자본 대비 최종 수익률 |

**6. 결과 저장**

- JSON: 거래 상세 데이터
- PNG: 차트 이미지

### 4.2 CLI 방식 (개발자)

**기본 백테스트:**

```python
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager

# 1. 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT')
dm.load_historical()

# 2. 전략 초기화
strategy = AlphaX7Core(use_mtf=True)

# 3. 백테스트 실행
trades = strategy.run_backtest(
    df_pattern=dm.df_pattern_full,
    df_entry=dm.df_entry_resampled,
    leverage=10,
    direction='Both',
    atr_mult=1.35,
    trail_start_r=1.5,
    trail_dist_r=0.25
)

# 4. 결과 출력
print(f"총 거래: {len(trades)}")
print(f"수익 거래: {len([t for t in trades if t['pnl'] > 0])}")
print(f"총 수익률: {sum(t['pnl'] for t in trades):.2f}%")
```

**고급 옵션:**

```python
trades = strategy.run_backtest(
    # ... (기본 파라미터)

    # MTF 필터
    use_mtf=True,               # 4H 추세 필터 사용

    # 트레일링 옵션
    enable_adaptive=True,       # RSI 기반 적응형 트레일링
    enable_pullback=True,       # 풀백 추가 진입

    # 리스크 관리
    max_loss_per_trade=5.0,     # 거래당 최대 손실 (%)
    daily_loss_limit=10.0        # 일일 손실 한도 (%)
)
```

### 4.3 결과 해석

**좋은 백테스트 기준:**

| 지표 | 최소 | 권장 | 우수 |
|------|------|------|------|
| 승률 | >50% | >65% | >80% |
| MDD | <30% | <20% | <10% |
| 샤프비율 | >1.0 | >1.5 | >2.0 |
| 총 수익률 | >100% | >500% | >1000% |
| 거래 수 | >20 | >50 | >100 |

**⚠️ 주의사항:**

1. **과최적화 (Overfitting)**
   - 승률 >95% → 의심 (과최적화 가능성)
   - 거래 수 <10 → 통계적 신뢰도 낮음

2. **백테스트 바이어스**
   - 미래 데이터 누수 확인
   - 슬리피지/수수료 포함 확인
   - 현실적 체결 가정

3. **실전 차이**
   - 백테스트: 이상적 조건
   - 실전: 네트워크 지연, 부분 체결, API 오류

---

## 5. 파라미터 최적화

### 5.1 최적화 목적

**목표:**
- 승률 최대화
- MDD 최소화
- 샤프비율 최적화
- 안정적 수익 곡선

**최적화 파라미터 (12개):**

| 파라미터 | 범위 | 설명 |
|----------|------|------|
| `atr_mult` | 0.8~2.0 | SL 거리 (ATR 배수) |
| `trail_start_r` | 1.0~3.0 | 트레일링 시작 (R 배수) |
| `trail_dist_r` | 0.1~0.5 | 트레일링 거리 (R 배수) |
| `rsi_period` | 7~21 | RSI 기간 |
| `rsi_oversold` | 20~40 | RSI 과매도 |
| `rsi_overbought` | 60~80 | RSI 과매수 |
| `leverage` | 1~20 | 레버리지 |
| `direction` | Long/Short/Both | 거래 방향 |

### 5.2 GUI 방식 (권장)

**1. 최적화 탭 선택**

**2. 설정**

- 거래소: Bybit
- 심볼: BTCUSDT
- 모드 선택:
  - **Quick**: 50개 조합 (~1분)
  - **Standard**: 5,000개 조합 (~30분)
  - **Deep**: 50,000개 조합 (~5시간)

**3. 실행**

- "시작" 버튼 클릭
- 진행률 실시간 표시
- CPU 사용률 100% 정상

**4. 결과 확인**

- 상위 10개 파라미터 조합 표시
- 승률/MDD/샤프비율 기준 정렬
- 클릭하여 상세 보기

**5. 프리셋 저장**

- "프리셋 저장" 버튼 클릭
- 이름: `BTCUSDT_Optimized_20260114`
- 저장 경로: `config/presets/`

### 5.3 CLI 방식 (개발자)

**Quick 최적화:**

```python
from core.optimizer import BacktestOptimizer, generate_quick_grid
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager

# 1. 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT')
dm.load_historical()

# 2. 그리드 생성 (Quick 모드)
grid = generate_quick_grid(trend_tf='1h')
print(f"총 조합 수: {len(grid)}")

# 3. 최적화 실행
optimizer = BacktestOptimizer(AlphaX7Core, dm.df_entry_full)
results = optimizer.run_optimization(
    df_pattern=dm.df_pattern_full,
    grid=grid
)

# 4. 베스트 결과
best = results[0]
print(f"승률: {best.win_rate:.1f}%")
print(f"MDD: {best.max_drawdown:.1f}%")
print(f"샤프비율: {best.sharpe_ratio:.2f}")
print(f"파라미터: {best.params}")
```

**Standard/Deep 최적화:**

```python
from core.optimizer import generate_standard_grid, generate_deep_grid

# Standard (5,000개 조합)
grid = generate_standard_grid(trend_tf='1h')

# Deep (50,000개 조합)
grid = generate_deep_grid(trend_tf='1h')

# 실행 (동일)
results = optimizer.run_optimization(
    df_pattern=dm.df_pattern_full,
    grid=grid
)
```

### 5.4 최적화 결과 활용

**프리셋 저장:**

```json
{
    "name": "BTCUSDT_Optimized",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "atr_mult": 1.35,
    "trail_start_r": 1.5,
    "trail_dist_r": 0.25,
    "leverage": 10,
    "direction": "Both",
    "win_rate": 88.4,
    "max_drawdown": 7.2,
    "total_return": 5375.0
}
```

**백테스트 재검증:**

1. 프리셋 로드
2. 다른 기간 데이터로 백테스트
3. 결과가 비슷하면 → 안정적
4. 결과가 크게 다르면 → 과최적화 의심

**심볼 간 적용:**

- BTCUSDT 최적화 결과 → ETHUSDT 테스트
- 메이저 알트 (BTC/ETH/BNB) → 공통 프리셋 가능
- 마이너 알트 → 개별 최적화 권장

---

## 6. 실매매 운영

### 6.1 사전 준비 체크리스트

**필수 준비:**

- [ ] API 키 발급 (거래소)
  - 거래 권한 활성화
  - IP 화이트리스트 설정 (선택)
  - API Secret 안전 보관
- [ ] 백테스트 검증 완료
  - 승률 >65%
  - MDD <20%
  - 최소 50회 거래
- [ ] 프리셋 저장
  - 최적화 완료된 파라미터
  - 또는 검증된 Default 프리셋
- [ ] 초기 자본 준비
  - Testnet: 무료 (연습용)
  - Mainnet: 최소 $100 (권장 $1,000)
- [ ] 리스크 관리 계획
  - 레버리지 결정 (권장 3~10x)
  - 일일 손실 한도 (권장 -10%)
  - 최대 포지션 크기

### 6.2 API 키 등록

**GUI 방식:**

1. **설정 탭** 선택
2. **API 관리** 클릭
3. 거래소 선택 (예: Bybit)
4. API Key / Secret 입력
5. **저장** (암호화됨)

**CLI 방식:**

```python
from storage.secure_storage import SecureStorage

storage = SecureStorage()
storage.save_api_key(
    exchange='bybit',
    api_key='YOUR_API_KEY',
    api_secret='YOUR_API_SECRET'
)
```

**보안:**
- 암호화 저장: `data/encrypted_keys.dat`
- AES-256 암호화
- 마스터 비밀번호 보호 (선택)

### 6.3 실매매 시작

**GUI 방식:**

1. **거래 탭** 선택
2. **설정:**
   - 거래소: Bybit
   - 심볼: BTCUSDT
   - 프리셋: `BTCUSDT_Optimized`
   - 금액: $1,000
   - 레버리지: 10x
   - 모드: 복리 (Total Capital)
3. **시작** 버튼 클릭
4. **실시간 모니터링:**
   - 현재 포지션: Long/Short/None
   - 진입 가격: $40,250
   - SL: $39,800 (트레일링)
   - 예상 손익: +2.3%
5. **중지** 시: "중지" 버튼 클릭

**CLI 방식:**

```python
from core.unified_bot import create_bot

# 1. 설정
config = {
    'symbol': 'BTCUSDT',
    'api_key': 'YOUR_API_KEY',
    'api_secret': 'YOUR_API_SECRET',
    'leverage': 10,
    'amount_usd': 1000,
    'preset_name': 'BTCUSDT_Optimized',
    'testnet': False  # Mainnet
}

# 2. 봇 생성
bot = create_bot('bybit', config)

# 3. 실행 (블로킹)
bot.run()

# 4. 중지 (다른 터미널에서)
bot.stop()
```

### 6.4 실시간 모니터링

**GUI 대시보드:**

| 정보 | 설명 |
|------|------|
| 현재 포지션 | Long/Short/None |
| 진입 가격 | 포지션 진입 가격 |
| 현재 가격 | 실시간 시장 가격 |
| SL 가격 | 손절가 (트레일링) |
| 예상 손익 | 현재 미실현 손익 |
| 레버리지 | 10x |
| 거래 이력 | 최근 10개 거래 |

**로그 모니터링:**

```bash
# 실시간 로그
tail -f logs/bot_bybit_btcusdt.log

# 주요 로그 메시지
# - "✅ Valid Long signal" → 진입 신호 확인
# - "🟢 Long ENTRY @ 40250" → 포지션 진입
# - "📈 Trailing SL → 39800" → SL 업데이트
# - "🔴 STOP LOSS HIT @ 39800" → SL 청산
# - "🟢 EXIT @ 42500, PnL: +5.3%" → 수익 청산
```

### 6.5 포지션 관리

**자동 관리 (봇이 처리):**

- ✅ 트레일링 SL 업데이트 (15분마다)
- ✅ RSI 기반 적응형 트레일링
- ✅ 풀백 추가 진입 (설정 시)
- ✅ 일일 손실 한도 체크
- ✅ 거래소 동기화 (5분마다)

**수동 개입 (긴급 상황):**

```python
# GUI: "강제 청산" 버튼

# CLI:
bot.force_close_position()
```

**상황별 대응:**

| 상황 | 대응 |
|------|------|
| 급격한 시장 변동 | 자동 SL 작동 (개입 불필요) |
| 네트워크 오류 | WebSocket 자동 재연결 |
| API 오류 | 재시도 (3회), 실패 시 중지 |
| 포지션 불일치 | 5분마다 자동 동기화 |
| 일일 손실 한도 초과 | 자동 거래 중지 |

### 6.6 복리 vs 고정 모드

**복리 모드 (권장):**

```
거래 1: $1,000 → 승리 +5% → $1,050
거래 2: $1,050 → 승리 +5% → $1,102.5
거래 3: $1,102.5 → 승리 +5% → $1,157.6
...
```

**고정 모드:**

```
거래 1: $1,000 → 승리 +$50 → $1,050 (다음 거래 $1,000)
거래 2: $1,000 → 승리 +$50 → $1,100 (다음 거래 $1,000)
거래 3: $1,000 → 승리 +$50 → $1,150 (다음 거래 $1,000)
...
```

**설정:**

```json
// data/capital_config.json
{
    "mode": "compounding",  // 또는 "fixed"
    "initial_capital": 1000,
    "current_capital": 1157.6
}
```

### 6.7 안전 운영 수칙

**레버리지 권장:**

| 경험 수준 | 레버리지 | 이유 |
|----------|---------|------|
| 초보자 | 3~5x | 안전 마진 확보 |
| 중급자 | 5~10x | 균형잡힌 수익/리스크 |
| 고급자 | 10~20x | 공격적 운영 (위험) |

**리스크 관리:**

```python
# 1. 거래당 최대 손실
max_loss_per_trade = 5%  # 권장 3~5%

# 2. 일일 손실 한도
daily_loss_limit = 10%   # 권장 10%

# 3. 최대 포지션 크기
max_position_size = total_capital * 0.5  # 권장 50%
```

**모니터링 주기:**

- **필수**: 일 2회 (아침/저녁) 상태 확인
- **권장**: 4시간마다 포지션 체크
- **긴급**: 급격한 시장 변동 시 실시간

---

## 7. 문제 해결

### 7.1 백테스트 관련

**문제: 백테스트가 실행되지 않음**

**원인:**
1. 데이터 캐시 없음
2. 파라미터 오류
3. 메모리 부족

**해결:**

```bash
# 1. 캐시 확인
ls data/cache/bybit_btcusdt_15m.parquet

# 2. 캐시 재생성
# GUI: 설정 탭 → 캐시 관리 → "업데이트"

# 3. 로그 확인
tail -f logs/backtest.log
```

**문제: 백테스트 결과가 이상함 (승률 0% 또는 100%)**

**원인:**
1. 데이터 품질 문제
2. 파라미터 극단값
3. 과최적화

**해결:**

```python
# 1. 데이터 확인
df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
print(df.describe())
print(df.isnull().sum())

# 2. 파라미터 리셋
# GUI: "기본값 로드" 버튼

# 3. 다른 기간 테스트
# 30일 → 60일 → 90일
```

### 7.2 최적화 관련

**문제: 최적화가 너무 느림**

**원인:**
1. Deep 모드 (50,000개 조합)
2. 데이터 크기 과다
3. CPU 성능 부족

**해결:**

```bash
# 1. Quick 모드 사용 (50개 조합)
# GUI: Quick 모드 선택

# 2. 데이터 크기 줄이기
# 1000 캔들 → 500 캔들

# 3. CPU 확인
# Task Manager → CPU 사용률 (100% 정상)
```

**문제: 최적화 결과가 백테스트와 다름**

**원인:**
1. 학습 기간 vs 테스트 기간 차이
2. 과최적화

**해결:**

```python
# 1. Train/Test Split
# 학습: 최근 6개월
# 테스트: 최근 1개월

# 2. Walk-Forward 분석
# 매월 최적화 → 다음 달 테스트

# 3. 안정성 확인
# 파라미터 약간 변경 시 결과 변화 확인
```

### 7.3 실매매 관련

**문제: 포지션 진입 안 됨**

**원인:**
1. 신호 조건 미충족
2. MTF 필터 차단
3. 자본 부족
4. API 오류

**해결:**

```bash
# 1. 로그 확인
tail -f logs/bot_bybit_btcusdt.log | grep "signal"

# 2. MTF 필터 확인
# 로그: "MTF Trend: down (required: up for Long)"
# → 4H 추세가 반대 방향

# 3. 자본 확인
# 로그: "Insufficient capital"
# → 거래소 잔고 확인

# 4. API 키 확인
# GUI: 설정 탭 → API 관리 → "테스트"
```

**문제: SL 자동 업데이트 안 됨**

**원인:**
1. WebSocket 연결 끊김
2. 트레일링 파라미터 오류
3. 거래소 API 오류

**해결:**

```bash
# 1. WebSocket 재연결
# 로그: "WebSocket reconnected"
# → 자동 재연결 (30초 이내)

# 2. 수동 동기화
# GUI: "동기화" 버튼 클릭

# 3. 파라미터 확인
# trail_start_r > 0
# trail_dist_r > 0
```

**문제: 포지션 불일치 (GUI vs 거래소)**

**원인:**
1. 동기화 지연
2. 수동 거래 개입
3. 캐시 오류

**해결:**

```bash
# 1. 강제 동기화
# GUI: "동기화" 버튼 클릭

# 2. 상태 파일 확인
cat storage/bybit_btcusdt_state.json

# 3. 상태 파일 삭제 (재초기화)
rm storage/bybit_btcusdt_state.json
# → 봇 재시작
```

### 7.4 데이터 관련

**문제: 캐시 갭 발생 (missing candles)**

**원인:**
1. WebSocket 연결 끊김
2. API 요청 실패
3. 거래소 다운타임

**해결:**

```bash
# 1. 자동 보충 (5분마다)
# 로그: "Gap detected, filling..."

# 2. 수동 보충
# GUI: 설정 탭 → 캐시 관리 → "보충"

# 3. 전체 재다운로드
# GUI: 설정 탭 → 캐시 관리 → "초기화" → "업데이트"
```

**문제: Parquet 파일 손상**

**원인:**
1. 디스크 오류
2. 쓰기 중 프로세스 종료

**해결:**

```bash
# 1. 백업 확인
ls backups/cache/

# 2. 복구
cp backups/cache/bybit_btcusdt_15m.parquet data/cache/

# 3. 재생성
rm data/cache/bybit_btcusdt_15m.parquet
# GUI: 캐시 관리 → "업데이트"
```

---

## 8. 안전 수칙

### 8.1 운영 전 체크리스트

**필수 확인:**

- [ ] Testnet에서 최소 1주일 테스트
- [ ] 백테스트 결과 안정적 (승률 >65%, MDD <20%)
- [ ] API 키 권한 확인 (거래만, 출금 불가)
- [ ] 초기 자본 손실 가능 범위 ($100~$1,000 권장)
- [ ] 레버리지 안전 범위 (3~10x)
- [ ] 일일 손실 한도 설정 (-10%)
- [ ] 모니터링 계획 (일 2회 이상)
- [ ] 비상 연락처 (거래소 지원팀)

### 8.2 리스크 관리 원칙

**1. 자본 배분 (Capital Allocation)**

```
총 자본: $10,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━
│ 거래 자본: $5,000 (50%)      │ ← 봇 운영
│ 예비 자금: $3,000 (30%)      │ ← 마진콜 대비
│ 비상 자금: $2,000 (20%)      │ ← 손실 보전
━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**2. 포지션 크기 (Position Sizing)**

```python
# 켈리 기준 (Kelly Criterion)
optimal_size = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

# 예시: 승률 70%, 평균 수익 5%, 평균 손실 3%
# optimal_size = (0.7 * 5 - 0.3 * 3) / 5 = 0.52 (52%)

# 안전 마진 적용 (50% 감소)
safe_size = optimal_size * 0.5 = 0.26 (26%)
```

**3. 레버리지 한도 (Leverage Limits)**

| 변동성 (ATR %) | 최대 레버리지 |
|----------------|--------------|
| 낮음 (<1%) | 20x |
| 중간 (1~3%) | 10x |
| 높음 (3~5%) | 5x |
| 매우 높음 (>5%) | 3x |

**4. 손실 한도 (Loss Limits)**

```python
# 거래당 손실 한도
max_loss_per_trade = 0.05  # 5%

# 일일 손실 한도
daily_loss_limit = 0.10    # 10%

# 주간 손실 한도
weekly_loss_limit = 0.20   # 20%

# 월간 손실 한도
monthly_loss_limit = 0.30  # 30%
```

### 8.3 금지 행위

**절대 금지:**

- ❌ **과도한 레버리지** (>20x)
- ❌ **손실 한도 무시** (계속 거래)
- ❌ **수동 개입** (봇 로직 방해)
- ❌ **복수 거래** (손실 후 즉시 재진입)
- ❌ **프리셋 무시** (검증 안 된 파라미터)
- ❌ **API 키 공유** (보안 위험)
- ❌ **모니터링 소홀** (3일 이상 방치)
- ❌ **백업 없이 운영** (상태 파일 손실 위험)

**주의 필요:**

- ⚠️ 하루 10회 이상 거래 (과매매)
- ⚠️ 승률 <50% 지속 (전략 재검토)
- ⚠️ MDD >30% (레버리지 낮추기)
- ⚠️ 포지션 24시간 이상 유지 (트렌드 변화 주의)

### 8.4 비상 대응

**시나리오 1: 급격한 시장 변동 (Flash Crash)**

```
대응:
1. 봇 자동 SL 작동 (개입 불필요)
2. 추가 진입 방지 (일일 손실 한도)
3. 시장 안정화 후 재시작
```

**시나리오 2: 거래소 API 장애**

```
대응:
1. 봇 자동 중지 (API 오류 감지)
2. 수동 청산 (거래소 웹/앱)
3. 복구 후 포지션 동기화
```

**시나리오 3: 연속 손실 (5회 이상)**

```
대응:
1. 봇 수동 중지
2. 전략 재검토 (백테스트 재실행)
3. 파라미터 조정 또는 프리셋 변경
4. 소액 테스트 후 재시작
```

**시나리오 4: 시스템 오류 (PC 종료, 네트워크 단절)**

```
대응:
1. 포지션 유지 (SL 거래소에 등록됨)
2. 시스템 복구 후 봇 재시작
3. 포지션 동기화 (자동)
4. 상태 파일 백업 확인
```

### 8.5 정기 점검 (Maintenance)

**일일 점검 (매일 2회):**

- [ ] 포지션 상태 확인
- [ ] 일일 손익 확인
- [ ] 로그 에러 확인
- [ ] 캐시 갭 확인

**주간 점검 (매주 1회):**

- [ ] 주간 손익 정산
- [ ] 승률/MDD 추세 확인
- [ ] 프리셋 성능 검토
- [ ] 상태 파일 백업

**월간 점검 (매월 1회):**

- [ ] 월간 수익률 분석
- [ ] 전략 재최적화 검토
- [ ] 시스템 업데이트 확인
- [ ] API 키 갱신 (필요 시)

---

## 9. 부록

### 9.1 주요 파일 경로

| 파일 | 경로 | 설명 |
|------|------|------|
| 메인 GUI | `run_gui.py` | GUI 실행 |
| 통합 봇 | `core/unified_bot.py` | 실매매 로직 |
| 백테스트 엔진 | `core/strategy_core.py` | 백테스트 로직 |
| 최적화 엔진 | `core/optimizer.py` | 파라미터 최적화 |
| 데이터 관리자 | `core/data_manager.py` | 캔들 관리 |
| 거래소 어댑터 | `exchanges/` | 거래소 API |
| 상태 저장소 | `storage/` | 봇 상태/거래 이력 |
| 캐시 | `data/cache/` | Parquet 데이터 |
| 로그 | `logs/` | 실행 로그 |

### 9.2 주요 명령어

**GUI 실행:**

```bash
cd f:\TwinStar-Quantum
./venv/Scripts/python.exe run_gui.py
```

**백테스트 (CLI):**

```bash
./venv/Scripts/python.exe -c "
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager

dm = BotDataManager('bybit', 'BTCUSDT')
dm.load_historical()

strategy = AlphaX7Core()
trades = strategy.run_backtest(
    df_pattern=dm.df_pattern_full,
    df_entry=dm.df_entry_resampled,
    leverage=10
)
print(f'총 거래: {len(trades)}')
"
```

**캐시 초기화:**

```bash
rm -rf data/cache/*
```

**로그 실시간 확인:**

```bash
tail -f logs/bot_bybit_btcusdt.log
```

### 9.3 용어 사전

| 용어 | 설명 |
|------|------|
| **ATR** | Average True Range (평균 진폭) |
| **MDD** | Maximum Drawdown (최대 낙폭) |
| **MTF** | Multi-Timeframe (다중 타임프레임) |
| **RSI** | Relative Strength Index (상대 강도 지수) |
| **SL** | Stop Loss (손절가) |
| **TP** | Take Profit (익절가) |
| **W/M 패턴** | Wyckoff Markup/Markdown 패턴 |
| **SSOT** | Single Source of Truth (단일 소스) |
| **Parquet** | 컬럼 기반 데이터 저장 포맷 |
| **프리셋** | 검증된 파라미터 조합 |
| **복리 모드** | 총 자본으로 거래 (수익 재투자) |
| **고정 모드** | 고정 금액으로 거래 |

### 9.4 참고 자료

- **프로젝트 문서**: `CLAUDE.md`, `README.md`
- **API 문서**: [CCXT Docs](https://docs.ccxt.com/)
- **Bybit API**: [Bybit API Docs](https://bybit-exchange.github.io/docs/)
- **Binance API**: [Binance API Docs](https://binance-docs.github.io/apidocs/)
- **커뮤니티**: GitHub Issues, Discord (추후 공개)

---

## 📞 지원

**문제 발생 시:**

1. 로그 확인: `logs/bot_*.log`
2. 문서 검색: `docs/`
3. GitHub Issues: [TwinStar-Quantum Issues](https://github.com/your-org/TwinStar-Quantum/issues)

**긴급 상황:**

- 봇 강제 중지: GUI "중지" 버튼 또는 `bot.stop()`
- 수동 청산: 거래소 웹/앱에서 직접 청산
- 백업 복구: `backups/` 디렉토리 참조

---

**문서 버전**: v1.0
**작성일**: 2026-01-14
**작성자**: Claude Opus 4.5
**라이선스**: MIT

---

**⚠️ 면책 조항:**

본 소프트웨어는 교육 및 연구 목적으로 제공됩니다. 암호화폐 거래는 높은 리스크를 동반하며, 투자 손실이 발생할 수 있습니다. 모든 거래 결정은 사용자 책임하에 이루어지며, 개발자는 어떠한 금전적 손실에 대해서도 책임지지 않습니다. 반드시 Testnet에서 충분히 테스트한 후 Mainnet에서 소액으로 시작하십시오.
