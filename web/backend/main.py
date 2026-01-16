"""
TwinStar Quantum - Web Backend API (v2.0.0)
FastAPI 기반 백엔드 서버 - 실제 core 모듈 통합
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ============= Core Imports =============
try:
    from core.optimizer import BacktestOptimizer, generate_fast_grid
    from core.strategy_core import AlphaX7Core
    from core.data_manager import BotDataManager
    from utils.preset_storage import PresetStorage
    from utils.metrics import calculate_backtest_metrics
    from config.constants import EXCHANGE_INFO, TF_MAPPING
    from config.parameters import DEFAULT_PARAMS, PARAM_RANGES_BY_MODE
    from utils.logger import get_module_logger
    CORE_AVAILABLE = True
except Exception as e:
    print(f"Warning: Core modules not available: {e}")
    CORE_AVAILABLE = False

logger = get_module_logger(__name__) if CORE_AVAILABLE else None

app = FastAPI(
    title="TwinStar Quantum API",
    description="암호화폐 자동매매 시스템 웹 API (v2.0.0)",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Global State =============
optimization_jobs: Dict[str, Dict[str, Any]] = {}
preset_storage: Optional['PresetStorage'] = None

# Initialize preset storage
if CORE_AVAILABLE:
    try:
        preset_storage = PresetStorage()
    except Exception as e:
        print(f"Warning: PresetStorage initialization failed: {e}")

# ============= Models =============
class TradeRequest(BaseModel):
    exchange: str
    symbol: str
    side: str  # "buy" or "sell"
    amount: float
    leverage: int = 1

class BacktestRequest(BaseModel):
    exchange: str
    symbol: str
    timeframe: str = "15m"
    params: Optional[Dict[str, Any]] = None

class OptimizationRequest(BaseModel):
    exchange: str
    symbol: str
    timeframe: str = "15m"
    mode: str = "standard"  # "quick", "standard", "deep"
    param_ranges: Optional[Dict[str, List[float]]] = None

class PresetRequest(BaseModel):
    name: str
    exchange: str
    symbol: str
    timeframe: str
    params: Dict[str, Any]

# ============= Helper Functions =============
def get_data_manager(exchange: str, symbol: str) -> BotDataManager:
    """BotDataManager 인스턴스 생성"""
    if not CORE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Core modules not available")
    return BotDataManager(exchange, symbol)

def get_optimizer(df) -> 'BacktestOptimizer':
    """BacktestOptimizer 인스턴스 생성"""
    if not CORE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Core modules not available")
    return BacktestOptimizer(AlphaX7Core, df)

# ============= API Routes =============

@app.get("/")
async def root():
    return {
        "message": "TwinStar Quantum API",
        "version": "2.0.0",
        "core_available": CORE_AVAILABLE,
        "features": [
            "Real Backtest Engine (core.optimizer)",
            "Meta Optimization System (v7.20)",
            "Preset Management (utils.preset_storage)",
            "3 Optimization Modes (Quick/Standard/Deep)"
        ]
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "core_modules": CORE_AVAILABLE,
        "version": "2.0.0"
    }

# ----------- Dashboard -----------
@app.get("/api/dashboard/status")
async def get_dashboard_status():
    """대시보드 상태 조회"""
    # TODO: 실제 UnifiedBot 연결
    return {
        "balance": {"total": 10000.0, "available": 8500.0, "in_position": 1500.0},
        "positions": [],
        "pnl": {"daily": 125.50, "weekly": 450.00, "monthly": 1200.00},
        "active_bots": 0,
        "core_available": CORE_AVAILABLE
    }

@app.get("/api/exchanges")
async def get_exchanges():
    """지원 거래소 목록"""
    if CORE_AVAILABLE:
        return {"exchanges": list(EXCHANGE_INFO.keys())}
    return {"exchanges": ["bybit", "binance", "okx", "bitget", "bingx", "upbit", "bithumb"]}

@app.get("/api/symbols/{exchange}")
async def get_symbols(exchange: str):
    """거래소별 심볼 목록"""
    # TODO: 실제 거래소 API 연결
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
               "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT"]
    return {"exchange": exchange, "symbols": symbols}

# ----------- Backtest -----------
@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    """실제 백테스트 실행"""
    if not CORE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Core modules not available")

    try:
        # 데이터 로드
        manager = get_data_manager(request.exchange, request.symbol)
        df = manager.get_full_history(with_indicators=False)

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="No data available")

        # 파라미터 준비
        params = request.params if request.params else DEFAULT_PARAMS.copy()

        # 백테스트 실행
        optimizer = get_optimizer(df)
        trades = optimizer.run_single_backtest(df, params)

        # 메트릭 계산
        metrics = calculate_backtest_metrics(trades, leverage=params.get('leverage', 10))

        return {
            "success": True,
            "exchange": request.exchange,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "data_points": len(df),
            "period": f"{df.iloc[0]['timestamp']} ~ {df.iloc[-1]['timestamp']}",
            "params": params,
            "metrics": metrics,
            "trades": trades[:50]  # 최근 50개만 반환
        }

    except Exception as e:
        logger.error(f"Backtest error: {e}") if logger else None
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backtest/params")
async def get_backtest_params():
    """백테스트 파라미터 기본값"""
    if CORE_AVAILABLE:
        return {"params": DEFAULT_PARAMS}

    return {"params": {
        "macd_fast": 6, "macd_slow": 18, "macd_signal": 7,
        "rsi_period": 14, "atr_period": 14, "atr_mult": 1.25,
        "leverage": 10
    }}

# ----------- Optimization -----------
@app.post("/api/optimization/start")
async def start_optimization(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """최적화 시작 (Quick/Standard/Deep 모드)"""
    if not CORE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Core modules not available")

    try:
        job_id = f"OPT_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 작업 초기화
        optimization_jobs[job_id] = {
            "status": "running",
            "progress": 0,
            "exchange": request.exchange,
            "symbol": request.symbol,
            "mode": request.mode,
            "started_at": datetime.now().isoformat(),
            "results": None,
            "error": None
        }

        # 백그라운드 작업 시작
        background_tasks.add_task(
            run_optimization_task,
            job_id,
            request.exchange,
            request.symbol,
            request.mode,
            request.param_ranges
        )

        return {
            "job_id": job_id,
            "status": "started",
            "mode": request.mode,
            "exchange": request.exchange,
            "symbol": request.symbol
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_optimization_task(
    job_id: str,
    exchange: str,
    symbol: str,
    mode: str,
    param_ranges: Optional[Dict[str, List[float]]]
):
    """백그라운드 최적화 작업"""
    try:
        # 데이터 로드
        manager = get_data_manager(exchange, symbol)
        df = manager.get_full_history(with_indicators=False)

        if df is None or df.empty:
            optimization_jobs[job_id]["status"] = "failed"
            optimization_jobs[job_id]["error"] = "No data available"
            return

        # 파라미터 범위 준비
        if param_ranges is None:
            param_ranges = PARAM_RANGES_BY_MODE.get(mode, PARAM_RANGES_BY_MODE["standard"])

        # 최적화 실행
        optimizer = get_optimizer(df)

        # 파라미터 그리드 생성
        if mode == "quick":
            # Quick 모드: 소수의 조합만
            grid = {k: v[:2] if isinstance(v, list) and len(v) >= 2 else v
                    for k, v in param_ranges.items()}
        else:
            grid = param_ranges

        results = optimizer.run_optimization(df, grid)

        # 결과 저장
        optimization_jobs[job_id]["status"] = "completed"
        optimization_jobs[job_id]["progress"] = 100
        optimization_jobs[job_id]["results"] = results[:20]  # 상위 20개만
        optimization_jobs[job_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        optimization_jobs[job_id]["status"] = "failed"
        optimization_jobs[job_id]["error"] = str(e)
        logger.error(f"Optimization error: {e}") if logger else None

@app.get("/api/optimization/status/{job_id}")
async def get_optimization_status(job_id: str):
    """최적화 진행 상태"""
    if job_id not in optimization_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = optimization_jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "exchange": job["exchange"],
        "symbol": job["symbol"],
        "mode": job["mode"],
        "started_at": job["started_at"],
        "completed_at": job.get("completed_at"),
        "results": job.get("results"),
        "error": job.get("error")
    }

@app.get("/api/optimization/modes")
async def get_optimization_modes():
    """최적화 모드 정보"""
    if not CORE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Core modules not available")

    return {
        "modes": {
            "quick": {
                "name": "Quick Mode",
                "combinations": "~8개",
                "time": "~2분",
                "description": "문서 권장값 우선 탐색"
            },
            "standard": {
                "name": "Standard Mode",
                "combinations": "~60개",
                "time": "~15분",
                "description": "균형잡힌 범위 탐색"
            },
            "deep": {
                "name": "Deep Mode",
                "combinations": "~1,080개",
                "time": "~4.5시간",
                "description": "전수 탐색"
            }
        },
        "param_ranges": PARAM_RANGES_BY_MODE
    }

# ----------- Presets -----------
@app.get("/api/presets/{exchange}/{symbol}/{timeframe}")
async def list_presets_for_symbol(exchange: str, symbol: str, timeframe: str):
    """심볼별 프리셋 목록"""
    if not CORE_AVAILABLE or preset_storage is None:
        return {"presets": []}

    try:
        presets = preset_storage.load_all_presets(symbol, timeframe)
        return {"presets": presets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/presets/{symbol}/{timeframe}/latest")
async def get_latest_preset(symbol: str, timeframe: str):
    """최신 프리셋 로드"""
    if not CORE_AVAILABLE or preset_storage is None:
        raise HTTPException(status_code=503, detail="Core modules not available")

    try:
        preset = preset_storage.load_preset(symbol, timeframe)
        if preset is None:
            raise HTTPException(status_code=404, detail="Preset not found")
        return {"preset": preset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/presets")
async def save_new_preset(request: PresetRequest):
    """프리셋 저장"""
    if not CORE_AVAILABLE or preset_storage is None:
        raise HTTPException(status_code=503, detail="Core modules not available")

    try:
        optimization_result = {
            "win_rate": 0.0,
            "mdd": 0.0,
            "profit_factor": 0.0,
            "total_return": 0.0
        }

        preset_storage.save_preset(
            symbol=request.symbol,
            tf=request.timeframe,
            params=request.params,
            optimization_result=optimization_result,
            exchange=request.exchange
        )
        return {"success": True, "message": f"Preset saved for {request.symbol} {request.timeframe}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/presets/{name}")
async def delete_preset(name: str):
    """프리셋 삭제"""
    # TODO: 실제 삭제 구현
    return {"success": True, "message": f"Preset '{name}' deleted"}

# ----------- History -----------
@app.get("/api/history/trades")
async def get_trade_history(
    limit: int = 50,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None
):
    """거래 내역 조회"""
    # TODO: 실제 DB 연결
    trades = [
        {"id": 1, "datetime": "2026-01-13 10:30:00", "exchange": "bybit",
         "symbol": "BTCUSDT", "side": "Long", "pnl": 125.50, "pnl_pct": 2.5},
        {"id": 2, "datetime": "2026-01-13 09:15:00", "exchange": "bybit",
         "symbol": "ETHUSDT", "side": "Short", "pnl": -45.20, "pnl_pct": -0.9},
        {"id": 3, "datetime": "2026-01-12 16:45:00", "exchange": "binance",
         "symbol": "SOLUSDT", "side": "Long", "pnl": 89.30, "pnl_pct": 1.8},
    ]
    return {"trades": trades, "total": len(trades)}

# ----------- Settings -----------
@app.get("/api/settings")
async def get_settings():
    """설정 조회"""
    return {
        "telegram": {"enabled": False, "chat_id": ""},
        "api_keys": {"bybit": False, "binance": False, "okx": False},
        "theme": "dark",
        "language": "ko"
    }

@app.post("/api/settings")
async def save_settings(settings: Dict[str, Any]):
    """설정 저장"""
    return {"success": True, "message": "설정이 저장되었습니다"}

# ----------- Data Collection -----------
@app.get("/api/data/timeframes")
async def get_timeframes():
    """지원 타임프레임"""
    if CORE_AVAILABLE:
        return {"timeframes": list(TF_MAPPING.keys())}
    return {"timeframes": ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]}

@app.post("/api/data/download")
async def download_data(exchange: str, symbol: str, timeframe: str, days: int = 30):
    """데이터 다운로드 요청"""
    # TODO: 실제 데이터 다운로드 구현
    return {
        "status": "started",
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days
    }

@app.get("/api/data/status/{exchange}/{symbol}")
async def get_data_status(exchange: str, symbol: str):
    """데이터 상태 확인"""
    if not CORE_AVAILABLE:
        return {"available": False, "count": 0}

    try:
        manager = get_data_manager(exchange, symbol)
        df = manager.get_full_history(with_indicators=False)

        if df is None or df.empty:
            return {"available": False, "count": 0}

        return {
            "available": True,
            "count": len(df),
            "start": df.iloc[0]['timestamp'].isoformat() if 'timestamp' in df.columns else None,
            "end": df.iloc[-1]['timestamp'].isoformat() if 'timestamp' in df.columns else None
        }
    except Exception:
        return {"available": False, "count": 0}

# ----------- Auto Trading -----------
@app.post("/api/auto/start")
async def start_auto_trading(config: Dict[str, Any]):
    """자동매매 시작"""
    # TODO: 실제 UnifiedBot 연결
    return {"status": "started", "bot_id": f"BOT_{datetime.now().strftime('%H%M%S')}"}

@app.post("/api/auto/stop")
async def stop_auto_trading():
    """자동매매 중지"""
    return {"status": "stopped"}

@app.get("/api/auto/status")
async def get_auto_status():
    """자동매매 상태"""
    return {
        "running": False,
        "uptime": 0,
        "trades_today": 0,
        "pnl_today": 0.0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
