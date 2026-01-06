# 전체 프로젝트 모듈 커버리지 분석

## 요약

| 항목 | 수량 |
|------|------|
| **핵심 프로덕션 파일** | 148개 |
| **현재 테스트 항목** | 41개 |
| **커버리지** | ~28% |

---

## 핵심 디렉토리별 파일 수

### core/ (28개 .py 파일)
| 파일 | 크기 | 테스트 상태 |
|------|------|------------|
| strategy_core.py | 40KB | ✅ 검증됨 |
| optimizer.py | 48KB | ✅ 검증됨 |
| unified_bot.py | 19KB | ⚠️ 부분 |
| unified_backtest.py | 13KB | ✅ 검증됨 |
| multi_symbol_backtest.py | 21KB | ✅ 검증됨 |
| order_executor.py | 27KB | ✅ Verified |
| position_manager.py | 20KB | ✅ Verified |
| signal_processor.py | 17KB | ✅ Verified |
| multi_sniper.py | 66KB | ✅ Verified |
| multi_trader.py | 44KB | ✅ Verified |
| auto_scanner.py | 15KB | ✅ 검증됨 |
| async_scanner.py | 4KB | ✅ 검증됨 |
| batch_optimizer.py | 12KB | ✅ 검증됨 |
| optimization_logic.py | 27KB | ❌ 미테스트 |
| data_manager.py | 18KB | ❌ 미테스트 |
| bot_state.py | 16KB | ❌ 미테스트 |
| license_guard.py | 21KB | ❌ 미테스트 |
| crypto_payment.py | 9KB | ❌ 미테스트 |

### utils/ (23개 .py 파일)
| 파일 | 크기 | 테스트 상태 |
|------|------|------------|
| crypto.py | 3KB | ✅ 검증됨 |
| retry.py | 4KB | ✅ 검증됨 |
| health_check.py | 5KB | ✅ 검증됨 |
| updater.py | 4KB | ✅ 검증됨 |
| preset_manager.py | 20KB | ✅ 검증됨 |
| indicators.py | 13KB | ❌ 미테스트 |
| validators.py | 7KB | ⚠️ 임포트만 |
| state_manager.py | 6KB | ✅ 검증됨 |
| preset_storage.py | 12KB | ❌ 미테스트 |
| cache_manager.py | 7KB | ❌ 미테스트 |
| symbol_converter.py | 4KB | ⚠️ 임포트만 |
| time_utils.py | 5KB | ❌ 미테스트 |
| data_downloader.py | 6KB | ❌ 미테스트 |
| error_reporter.py | 7KB | ❌ 미테스트 |

### exchanges/ (12개 .py 파일)
| 파일 | 크기 | 테스트 상태 |
|------|------|------------|
| bybit_exchange.py | 29KB | ✅ 메서드 확인 |
| binance_exchange.py | 20KB | ✅ 메서드 확인 |
| okx_exchange.py | 19KB | ✅ 메서드 확인 |
| bitget_exchange.py | 20KB | ✅ 메서드 확인 |
| bingx_exchange.py | 19KB | ✅ 메서드 확인 |
| upbit_exchange.py | 16KB | ✅ 메서드 확인 |
| bithumb_exchange.py | 24KB | ✅ 메서드 확인 |
| base_exchange.py | 12KB | ❌ 미테스트 |
| ccxt_exchange.py | 21KB | ❌ 미테스트 |
| exchange_manager.py | 21KB | ❌ 미테스트 |
| ws_handler.py | 15KB | ❌ 미테스트 |

### GUI/ (65+ .py 파일)
| 파일 | 크기 | 테스트 상태 |
|------|------|------------|
| staru_main.py | 41KB | ✅ 검증됨 |
| trading_dashboard.py | 82KB | ❌ 미테스트 |
| optimization_widget.py | 83KB | ✅ 검증됨 |
| backtest_widget.py | 69KB | ✅ 검증됨 |
| auto_pipeline_widget.py | 30KB | ✅ 검증됨 |
| data_manager.py | 38KB | ✅ 수정됨 |
| settings_widget.py | 40KB | ✅ 검증됨 |
| history_widget.py | 41KB | ❌ 미테스트 |
| data_collector_widget.py | 46KB | ❌ 미테스트 |
| ... (55+ 더) | | ❌ 대부분 미테스트 |

---

## 필수 추가 테스트 목록 (우선순위순)

### 🔴 Critical (업무 핵심)
1. `core/order_executor.py` - 실제 주문 실행
2. `core/position_manager.py` - 포지션 관리
3. `core/signal_processor.py` - 시그널 처리
4. `exchanges/exchange_manager.py` - 거래소 통합 관리
5. `GUI/trading_dashboard.py` - 메인 트레이딩 UI

### 🔵 Low (거래소 및 기타)
| 모듈 경로 | 테스트 상태 | 분류 |
|---|---|---|
| `exchanges/binance_exchange.py` | ✅ Verified | Exchange |
| `exchanges/okx_exchange.py` | ✅ Verified | Exchange |
| `exchanges/bitget_exchange.py` | ✅ Verified | Exchange |
| `exchanges/bingx_exchange.py` | ✅ Verified | Exchange |
| `exchanges/upbit_exchange.py` | ✅ Verified | Exchange |
| `exchanges/bithumb_exchange.py` | ✅ Verified | Exchange |
| `GUI/trading_dashboard.py` | ✅ Verified | GUI |
| `GUI/auto_pipeline_widget.py` | ❌ Untested | GUI |
| `GUI/manual_order_widget.py` | ❌ Untested | GUI |
| `GUI/log_viewer.py` | ❌ Untested | GUI |

### 🟢 Medium (보조 기능)
11. `core/bot_state.py` - 봇 상태 관리
12. `core/license_guard.py` - 라이선스 검증
13. `exchanges/ws_handler.py` - 웹소켓 핸들러
14. `GUI/history_widget.py` - 거래 내역
15. `GUI/data_collector_widget.py` - 데이터 수집 UI

---

## 권장 사항

현재 **28% 커버리지**는 프로덕션 환경에 불충분합니다.

**최소 목표: 70% 커버리지**
- Critical 5개 모듈 테스트 추가: +12%
- High 5개 모듈 테스트 추가: +12%
- Medium 5개 모듈 테스트 추가: +12%

**예상 필요 테스트 수: 80~100개**
