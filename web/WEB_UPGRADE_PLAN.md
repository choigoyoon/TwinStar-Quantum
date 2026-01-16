# 웹 버전 업그레이드 계획 (v1.8.3 → v2.0.0)

## 현재 상태 분석

### 파일 구조
```
web/
├── backend/
│   └── main.py (7.3KB, 199줄) - FastAPI 백엔드
├── frontend/
│   ├── index.html (110KB, 2000+줄) - Vue.js SPA
│   └── guide_data.js (16KB) - 가이드 콘텐츠
└── run_server.py (3.9KB) - 서버 실행 스크립트
```

### 문제점
1. **단일 파일 SPA**: index.html에 2000+줄 (HTML + CSS + JavaScript)
2. **하드코딩 스타일**: CSS 변수 사용하지만 PyQt6 디자인 시스템과 불일치
3. **시뮬레이션 API**: 실제 core 로직과 연결되지 않음
4. **v7.20 기능 미반영**: 메타 최적화, 최신 파라미터 등

## 업그레이드 목표

### Phase 1: 백엔드 통합 (우선순위 1)
- ✅ 실제 core 모듈 연결
- ✅ 백테스트 API → core.optimizer
- ✅ 최적화 API → core.optimizer (v7.20)
- ✅ 대시보드 API → core.unified_bot
- ✅ 프리셋 API → utils.preset_storage

### Phase 2: 프론트엔드 모듈화 (우선순위 2)
- ✅ index.html 분리 (컴포넌트화)
- ✅ 디자인 시스템 통합 (ui.design_system 참조)
- ✅ Vue 3 Composition API 적용
- ✅ TypeScript 도입 (선택)

### Phase 3: 실시간 기능 (우선순위 3)
- ✅ WebSocket 지원 (거래소 연결)
- ✅ 실시간 차트 업데이트
- ✅ 실시간 포지션 모니터링

## 구현 계획

### Step 1: 백엔드 API 업그레이드 (2시간)

#### 1.1 실제 모듈 Import
```python
# web/backend/main.py
from core.optimizer import Optimizer
from core.unified_bot import UnifiedBot
from core.data_manager import BotDataManager
from utils.preset_storage import load_preset, save_preset, list_presets
from utils.metrics import calculate_backtest_metrics
from config.constants import EXCHANGE_INFO, TF_MAPPING
from config.parameters import DEFAULT_PARAMS, PARAM_RANGES_BY_MODE
```

#### 1.2 백테스트 API 구현
```python
@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    """실제 백테스트 실행"""
    try:
        # BotDataManager로 데이터 로드
        manager = BotDataManager(request.exchange, request.symbol)
        df = manager.load_entry_data()

        # Optimizer로 백테스트 실행
        optimizer = Optimizer(request.exchange, request.symbol)
        results = optimizer.run_single_backtest(df, request.params)

        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 1.3 최적화 API 구현 (v7.20)
```python
@app.post("/api/optimization/start")
async def start_optimization(request: OptimizationRequest):
    """실제 최적화 실행 (Quick/Standard/Deep 모드)"""
    optimizer = Optimizer(request.exchange, request.symbol)

    # 백그라운드 작업으로 실행
    job_id = f"OPT_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 비동기 실행 (celery 또는 threading)
    results = optimizer.optimize_parameters(
        mode=request.mode,  # "quick", "standard", "deep"
        param_ranges=request.param_ranges
    )

    return {"job_id": job_id, "status": "started"}
```

#### 1.4 프리셋 API
```python
@app.get("/api/presets")
async def list_all_presets():
    """저장된 프리셋 목록"""
    presets = list_presets()
    return {"presets": presets}

@app.get("/api/presets/{name}")
async def get_preset(name: str):
    """프리셋 로드"""
    preset = load_preset(name)
    return {"preset": preset}

@app.post("/api/presets")
async def save_new_preset(request: PresetRequest):
    """프리셋 저장"""
    save_preset(request.name, request.params)
    return {"success": True}
```

### Step 2: 디자인 시스템 통합 (1시간)

#### 2.1 CSS 변수 → 디자인 토큰
```javascript
// ui.design_system.tokens와 일치
:root {
    /* Colors - ui/design_system/tokens.py 참조 */
    --bg-base: #1a1b1e;
    --bg-surface: #25262b;
    --text-primary: #e4e6eb;
    --text-secondary: #a0a2a8;
    --accent-primary: #00d4ff;
    --accent-secondary: #bf40bf;
    --success: #00ff88;
    --danger: #ff0055;
    --warning: #ffaa00;

    /* Typography */
    --text-xs: 11px;
    --text-sm: 12px;
    --text-base: 14px;
    --text-lg: 16px;
    --text-xl: 20px;
    --text-2xl: 24px;

    /* Spacing */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-6: 24px;

    /* Radius */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
}
```

#### 2.2 컴포넌트 스타일 통일
- 버튼 → ui/design_system/styles/buttons.py 참조
- 입력 필드 → ui/design_system/styles/inputs.py 참조
- 카드 → ui/design_system/styles/cards.py 참조

### Step 3: 프론트엔드 모듈화 (3시간)

#### 3.1 디렉토리 구조
```
web/frontend/
├── index.html (진입점, 최소화)
├── js/
│   ├── app.js (Vue 앱 초기화)
│   ├── api.js (API 클라이언트)
│   ├── components/
│   │   ├── Dashboard.js
│   │   ├── Backtest.js
│   │   ├── Optimization.js
│   │   ├── Trading.js
│   │   └── Settings.js
│   └── utils/
│       ├── formatters.js
│       └── validators.js
├── css/
│   ├── tokens.css (디자인 토큰)
│   └── styles.css (컴포넌트 스타일)
└── guide_data.js (유지)
```

#### 3.2 Vue 컴포넌트 분리
```javascript
// js/components/Backtest.js
export default {
    template: `
        <div class="backtest-container">
            <div class="card p-6">
                <h2 class="text-xl font-bold mb-4">백테스트</h2>
                <!-- 백테스트 UI -->
            </div>
        </div>
    `,
    data() {
        return {
            exchange: 'bybit',
            symbol: 'BTCUSDT',
            timeframe: '15m',
            params: {}
        }
    },
    methods: {
        async runBacktest() {
            const result = await api.backtest({
                exchange: this.exchange,
                symbol: this.symbol,
                timeframe: this.timeframe,
                params: this.params
            })
            this.results = result
        }
    }
}
```

### Step 4: WebSocket 실시간 기능 (2시간)

#### 4.1 WebSocket 엔드포인트
```python
# web/backend/main.py
from fastapi import WebSocket

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 실시간 대시보드 데이터 전송
            data = {
                "balance": get_current_balance(),
                "positions": get_current_positions(),
                "pnl": get_current_pnl()
            }
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except:
        pass
```

#### 4.2 프론트엔드 WebSocket
```javascript
// js/utils/websocket.js
class DashboardWebSocket {
    constructor(url) {
        this.ws = new WebSocket(url)
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            this.onUpdate(data)
        }
    }

    onUpdate(data) {
        // Vue 상태 업데이트
    }
}
```

## 타임라인

### Day 1 (4시간)
- ✅ Step 1: 백엔드 API 업그레이드 (2시간)
- ✅ Step 2: 디자인 시스템 통합 (1시간)
- ✅ 테스트 및 디버그 (1시간)

### Day 2 (4시간)
- ✅ Step 3: 프론트엔드 모듈화 (3시간)
- ✅ 테스트 및 통합 (1시간)

### Day 3 (3시간) - 선택
- ✅ Step 4: WebSocket 실시간 기능 (2시간)
- ✅ 최종 테스트 (1시간)

## 우선순위

### 🔴 High Priority (Day 1)
1. 백엔드 실제 모듈 연결
2. 백테스트 API 실제 구현
3. 최적화 API (v7.20 Quick/Standard/Deep)
4. 프리셋 API

### 🟡 Medium Priority (Day 2)
5. 디자인 시스템 통합
6. 프론트엔드 모듈화
7. 컴포넌트 분리

### 🟢 Low Priority (Day 3)
8. WebSocket 실시간 기능
9. 실시간 차트
10. TypeScript 도입

## 성공 기준

### Minimum Viable Product (MVP)
- ✅ 실제 백테스트 실행 가능
- ✅ 최적화 3가지 모드 (Quick/Standard/Deep)
- ✅ 프리셋 저장/로드
- ✅ 디자인 시스템 일관성

### Nice to Have
- ✅ WebSocket 실시간 업데이트
- ✅ Vue 3 Composition API
- ✅ TypeScript
- ✅ 모바일 반응형

## 다음 단계

1. **백엔드 우선 업그레이드**
   - 기존 시뮬레이션 API를 실제 core 모듈로 교체
   - v7.20 메타 최적화 시스템 통합

2. **디자인 시스템 통합**
   - ui.design_system.tokens 참조
   - PyQt6 GUI와 시각적 일관성

3. **프론트엔드 리팩토링** (선택)
   - 단일 파일 → 모듈화
   - 유지보수성 향상

4. **실시간 기능 추가** (선택)
   - WebSocket 연결
   - 실시간 모니터링

---

**시작 단계**: Step 1 (백엔드 API 업그레이드)
**예상 시간**: 2시간
**다음 커밋**: `feat: 웹 백엔드 API 실제 모듈 통합 (v2.0.0)`
