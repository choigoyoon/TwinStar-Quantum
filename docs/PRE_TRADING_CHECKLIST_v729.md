# 🚀 실전 매매 전 최종 체크리스트 (v7.29)

> **작성일**: 2026-01-20
> **대상**: TwinStar-Quantum 실전 매매 시작 전 필수 검증

---

## ✅ 1단계: 시스템 무결성 확인 (5분)

### 1.1 환경 검증
```bash
# 가상환경 확인
where python
# → f:\TwinStar-Quantum\venv\Scripts\python.exe

# 프로젝트 루트
cd
# → f:\TwinStar-Quantum

# Python 버전
python --version
# → Python 3.12

# 의존성 확인
pip list | findstr "ccxt PyQt6 pandas"
# → ccxt 4.2.0+, PyQt6 6.6.0+, pandas 2.1.0+
```

### 1.2 코드 무결성
```bash
# Pyright 에러 확인
# VS Code Problems 탭: 0개 에러

# Git 상태 확인
git status
# → On branch feat/indicator-ssot-integration
# → nothing to commit, working tree clean

# 최신 커밋
git log -1 --oneline
# → docs: v7.29 Adaptive 최적화 성능 문서 작성
```

**결과**: ✅ / ❌

---

## ✅ 2단계: 거래소 연결 테스트 (10분)

### 2.1 API 키 검증
```bash
python tools/test_api_connection.py
```

**예상 출력**:
```
[Bybit] API Key: ✅ 유효
[Bybit] 계정 잔고: 1,000.00 USDT
[Bybit] 레버리지: 10x (설정됨)
[Bybit] 포지션: None (청산됨)
```

**체크**:
- [ ] API Key 유효
- [ ] 잔고 확인 (최소 100 USDT 이상)
- [ ] 레버리지 설정 (1-20x)
- [ ] 기존 포지션 청산

**결과**: ✅ / ❌

### 2.2 WebSocket 연결
```bash
python tools/test_websocket.py
```

**예상 출력**:
```
[WebSocket] 연결 성공
[WebSocket] BTC/USDT 구독 완료
[WebSocket] 실시간 데이터 수신 중...
  - Timestamp: 2026-01-20 14:30:00
  - Price: 50,000.00 USDT
  - Volume: 1,234.56 BTC
```

**체크**:
- [ ] WebSocket 연결 성공
- [ ] 실시간 데이터 수신 (>10개 틱)
- [ ] 데이터 품질 (no NaN)

**결과**: ✅ / ❌

---

## ✅ 3단계: 백테스트 검증 (15분)

### 3.1 최신 데이터 백테스트
```bash
python tools/validate_live_strategy.py
```

**예상 출력**:
```
===== 백테스트 결과 (최근 30일) =====
심볼: BTC/USDT
타임프레임: 1h
데이터 기간: 2025-12-21 ~ 2026-01-20 (720개 캔들)

승률: 83.75%
MDD: 10.86%
Sharpe Ratio: 18.0
거래 횟수: 24회 (0.8회/일)
단리 수익: 76.2%
복리 수익: 78.5%
안전 레버리지: 9.2x

등급: A (우수)
====================================
```

**체크**:
- [ ] 승률 ≥ 75%
- [ ] MDD ≤ 15%
- [ ] Sharpe Ratio ≥ 15.0
- [ ] 거래 빈도 0.5-1.0회/일
- [ ] 등급 A/B

**결과**: ✅ / ❌

### 3.2 최적 파라미터 확인
```bash
python tools/load_best_preset.py
```

**예상 출력**:
```
===== 최적 프리셋 (bybit_BTCUSDT_1h_macd.json) =====
atr_mult: 1.5
filter_tf: 4h
trail_start_r: 1.2
trail_dist_r: 0.03
entry_validity_hours: 6.0
leverage: 1

SSOT 버전: v7.24
MDD 신뢰도: ±1% ✅
클램핑: 제거됨 ✅
=============================================
```

**체크**:
- [ ] 프리셋 파일 존재
- [ ] SSOT 버전 v7.24 이상
- [ ] 파라미터 유효 범위 내

**결과**: ✅ / ❌

---

## ✅ 4단계: 리스크 관리 설정 (10분)

### 4.1 자본 배분
```python
# data/capital_config.json 확인
{
  "total_capital": 1000.0,  # 총 자본 (USDT)
  "max_position_size": 0.1,  # 최대 포지션 크기 (10%)
  "reserve_ratio": 0.2,      # 비상 준비금 (20%)
  "leverage": 5              # 레버리지 (1-20x)
}
```

**체크**:
- [ ] total_capital 설정 (실제 잔고와 일치)
- [ ] max_position_size ≤ 0.2 (20% 이하)
- [ ] reserve_ratio ≥ 0.1 (10% 이상)
- [ ] leverage ≤ 안전 레버리지 (백테스트 기준)

**권장 설정**:
- 초보자: `leverage=1-3`, `max_position_size=0.05`
- 중급자: `leverage=3-5`, `max_position_size=0.1`
- 고급자: `leverage=5-10`, `max_position_size=0.2`

**결과**: ✅ / ❌

### 4.2 손절/익절 설정
```python
# config/parameters.py 확인
DEFAULT_PARAMS = {
    'atr_mult': 1.5,         # 손절 배수
    'trail_start_r': 1.2,    # 트레일링 시작 (1.2R)
    'trail_dist_r': 0.03,    # 트레일링 간격 (3%)
}
```

**체크**:
- [ ] atr_mult 1.25-2.0 (권장)
- [ ] trail_start_r 1.0-2.0 (권장)
- [ ] trail_dist_r 0.02-0.05 (권장)

**결과**: ✅ / ❌

---

## ✅ 5단계: 모니터링 시스템 (5분)

### 5.1 로깅 확인
```bash
# 로그 디렉토리 확인
dir logs\trading_*.log
# → logs\trading_20260120.log (오늘 날짜 로그)

# 로그 레벨 확인
type logs\trading_20260120.log | findstr "level"
# → level=INFO (권장: INFO 또는 DEBUG)
```

**체크**:
- [ ] 로그 파일 생성됨
- [ ] 로그 레벨 INFO 이상
- [ ] 로그 기록 정상 (최근 10분 내 로그 있음)

**결과**: ✅ / ❌

### 5.2 알림 설정
```bash
# 텔레그램 봇 테스트
python tools/test_telegram.py
```

**예상 출력**:
```
[Telegram] 봇 연결 성공
[Telegram] 메시지 전송 테스트...
  → "🤖 TwinStar-Quantum 알림 테스트"
[Telegram] 전송 완료 ✅
```

**체크**:
- [ ] 텔레그램 봇 토큰 유효
- [ ] Chat ID 설정됨
- [ ] 테스트 메시지 수신됨

**결과**: ✅ / ❌

---

## ✅ 6단계: 시뮬레이션 테스트 (30분)

### 6.1 Paper Trading (모의 거래)
```bash
python run_gui.py --paper-trading
```

**테스트 시나리오**:
1. GUI 실행
2. "자동매매 시작" 버튼 클릭
3. 신호 발생 대기 (최대 30분)
4. 진입/청산 확인
5. 수익/손실 기록

**체크**:
- [ ] 신호 감지 정상
- [ ] 주문 실행 정상 (Paper Trading)
- [ ] 포지션 관리 정상
- [ ] 손절/익절 작동
- [ ] 수익/손실 기록

**결과**: ✅ / ❌

### 6.2 극단 시나리오 테스트
```bash
python tools/test_extreme_scenarios.py
```

**테스트 항목**:
- 급등/급락 대응
- WebSocket 끊김 복구
- API 에러 핸들링
- 동시 신호 발생
- 자본 부족 처리

**체크**:
- [ ] 5개 시나리오 모두 통과

**결과**: ✅ / ❌

---

## ✅ 7단계: 최종 확인 (5분)

### 7.1 체크리스트 요약
| 단계 | 항목 | 결과 |
|------|------|------|
| 1 | 시스템 무결성 | ⬜ |
| 2 | 거래소 연결 | ⬜ |
| 3 | 백테스트 검증 | ⬜ |
| 4 | 리스크 관리 | ⬜ |
| 5 | 모니터링 | ⬜ |
| 6 | 시뮬레이션 | ⬜ |

**총점**: ⬜ / 6

### 7.2 최종 승인
- [ ] 모든 단계 ✅ 완료
- [ ] 백테스트 등급 A/B
- [ ] Paper Trading 성공
- [ ] 리스크 관리 설정 완료
- [ ] 모니터링 시스템 작동

**승인 서명**: ________________
**승인 일시**: 2026-01-20 __:__

---

## ⚠️ 중요 주의사항

### 절대 금지 사항
1. ❌ **백테스트 없이 실전** - 최소 30일 백테스트 필수
2. ❌ **과도한 레버리지** - 안전 레버리지 초과 금지
3. ❌ **전액 투자** - 비상 준비금 20% 필수 유지
4. ❌ **수동 개입** - 자동매매 중 수동 거래 금지
5. ❌ **파라미터 변경** - 실전 중 파라미터 변경 금지

### 권장 사항
1. ✅ **소액으로 시작** - 총 자본의 10-20%로 시작
2. ✅ **1주일 모니터링** - 첫 주는 집중 모니터링
3. ✅ **매일 결과 확인** - 일일 수익률/MDD 체크
4. ✅ **월간 재검증** - 매월 백테스트 재실행
5. ✅ **손실 한도 설정** - 일일/월간 손실 한도 설정

### 긴급 상황 대응
```bash
# 즉시 중단 (긴급)
python tools/emergency_stop.py

# 모든 포지션 청산
python tools/close_all_positions.py

# 봇 재시작
python run_gui.py --restart
```

---

## 📊 실전 매매 시작 후 모니터링

### 일일 체크리스트 (매일 21시)
- [ ] 오늘 거래 내역 확인 (횟수, 승률, PnL)
- [ ] 현재 MDD 확인 (15% 초과 시 경고)
- [ ] 로그 에러 확인 (ERROR 레벨 로그)
- [ ] 텔레그램 알림 확인 (놓친 알림 없는지)
- [ ] 잔고 확인 (예상 잔고와 실제 잔고 일치)

### 주간 체크리스트 (매주 일요일)
- [ ] 주간 수익률 계산 (목표 대비 달성도)
- [ ] 주간 거래 횟수 확인 (3-7회 권장)
- [ ] 파라미터 유효성 재검증 (백테스트)
- [ ] 시스템 업데이트 확인 (Git pull)
- [ ] 백업 생성 (DB, 로그, 설정 파일)

### 월간 체크리스트 (매월 1일)
- [ ] 월간 성과 리포트 작성 (수익률, MDD, Sharpe)
- [ ] 백테스트 재실행 (최근 90일 데이터)
- [ ] 파라미터 재최적화 (필요 시)
- [ ] 리스크 관리 재설정 (자본 증감에 따라)
- [ ] 전략 유효성 검증 (승률 80% 이상 유지)

---

## 🎯 성공 기준

### 단기 목표 (1주)
- 거래 횟수: 5-7회
- 승률: ≥ 70%
- MDD: ≤ 5%
- 시스템 안정성: 99% 이상

### 중기 목표 (1개월)
- 월간 수익률: ≥ 10%
- 승률: ≥ 75%
- MDD: ≤ 10%
- Sharpe Ratio: ≥ 2.0

### 장기 목표 (3개월)
- 분기 수익률: ≥ 30%
- 승률: ≥ 80%
- MDD: ≤ 15%
- Sharpe Ratio: ≥ 3.0

---

## 📞 지원 및 문의

- GitHub Issues: https://github.com/username/TwinStar-Quantum/issues
- 텔레그램: @twinstar_quantum_support
- 이메일: support@twinstar-quantum.com

---

**작성자**: Claude Opus 4.5
**최종 업데이트**: 2026-01-20
**버전**: v7.29
