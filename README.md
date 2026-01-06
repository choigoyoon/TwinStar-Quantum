# TwinStar Quantum

## 개요

TwinStar Quantum은 암호화폐 자동 매매 시스템입니다.

## 주요 기능

- **자동 최적화**: 전략 파라미터 자동 탐색
- **백테스트**: 과거 데이터 기반 전략 검증
- **자동 스캐너**: 다중 심볼 실시간 감시
- **실시간 매매**: 자동 진입/청산 실행
- **멀티 거래소**: Bybit, Binance, OKX, Bitget, Bingx, Upbit, Bithumb 지원

## 설치

### 요구사항

- Python 3.10+
- Windows 10/11

### 설치 방법

```bash
# 1. 저장소 클론
git clone https://github.com/your/twinstar-quantum.git
cd twinstar-quantum

# 2. 가상환경 생성
python -m venv venv
venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 실행
python GUI/staru_main.py
```

## 디렉토리 구조

```
TwinStar Quantum/
├── GUI/                 # GUI 모듈
│   ├── staru_main.py   # 메인 윈도우
│   ├── constants.py    # 공용 상수
│   └── ...
├── core/               # 핵심 로직
│   ├── strategy_core.py
│   ├── optimizer.py
│   ├── unified_bot.py
│   └── ...
├── exchanges/          # 거래소 어댑터
│   ├── bybit_exchange.py
│   ├── binance_exchange.py
│   └── ...
├── utils/              # 유틸리티
│   ├── preset_manager.py
│   ├── validators.py
│   └── ...
├── config/             # 설정
│   ├── parameters.py   # 전략 파라미터
│   └── presets/        # 저장된 프리셋
├── tests/              # 테스트
│   ├── unit/
│   ├── integration/
│   └── ...
└── paths.py            # 경로 관리
```

## 사용법

### 1. 최적화

1. 최적화 탭에서 심볼 선택
2. Quick/Standard/Deep 모드 선택
3. "시작" 클릭
4. 결과 확인 후 프리셋 저장

### 2. 백테스트

1. 백테스트 탭에서 프리셋 로드
2. 기간 설정
3. "실행" 클릭
4. 결과 분석

### 3. 자동매매

1. 매매 탭에서 거래소 연결
2. 프리셋 선택
3. 금액/레버리지 설정
4. "시작" 클릭

## 설정

### 거래소 API 키

1. 설정 탭 → API 관리
2. 거래소 선택 → 키 입력
3. 저장

### 파라미터

주요 파라미터는 `config/parameters.py`에서 관리:

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| atr_mult | ATR 배수 | 1.25 |
| rsi_period | RSI 기간 | 14 |
| leverage | 레버리지 | 10 |
| slippage | 슬리피지 | 0.0006 |

## 테스트

```bash
# 단위 테스트
python -m unittest discover -s tests/unit -v

# 통합 테스트
python -m unittest discover -s tests/integration -v

# 전체 플로우 테스트
python tests/test_full_flow_sequence.py
```

## 빌드

```bash
# EXE 빌드
pyinstaller staru_clean.spec

# 결과물
dist/TwinStar Quantum.exe
```

## 라이선스

Proprietary Software. All Rights Reserved.

## 문의

support@youngstreet.co.kr
