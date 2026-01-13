"""
TwinStar Quantum - Web Backend API
FastAPI 기반 백엔드 서버
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

app = FastAPI(
    title="TwinStar Quantum API",
    description="암호화폐 자동매매 시스템 웹 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Models =============
class TradeRequest(BaseModel):
    exchange: str
    symbol: str
    side: str  # "buy" or "sell"
    amount: float
    leverage: int = 1

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    params: Optional[Dict[str, Any]] = None

class OptimizationRequest(BaseModel):
    symbol: str
    timeframe: str
    param_ranges: Dict[str, List[float]]

# ============= API Routes =============

@app.get("/")
async def root():
    return {"message": "TwinStar Quantum API", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ----------- Dashboard -----------
@app.get("/api/dashboard/status")
async def get_dashboard_status():
    """대시보드 상태 조회"""
    return {
        "balance": {"total": 10000.0, "available": 8500.0, "in_position": 1500.0},
        "positions": [],
        "pnl": {"daily": 125.50, "weekly": 450.00, "monthly": 1200.00},
        "active_bots": 0
    }

@app.get("/api/exchanges")
async def get_exchanges():
    """지원 거래소 목록"""
    try:
        from config.constants import EXCHANGE_INFO
        return {"exchanges": list(EXCHANGE_INFO.keys())}
    except Exception:

        return {"exchanges": ["bybit", "binance", "okx", "bitget", "bingx", "upbit", "bithumb"]}

@app.get("/api/symbols/{exchange}")
async def get_symbols(exchange: str):
    """거래소별 심볼 목록"""
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", 
               "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT"]
    return {"exchange": exchange, "symbols": symbols}

# ----------- Trading -----------
@app.post("/api/trade")
async def execute_trade(request: TradeRequest):
    """거래 실행 (시뮬레이션)"""
    return {
        "success": True,
        "order_id": f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "exchange": request.exchange,
        "symbol": request.symbol,
        "side": request.side,
        "amount": request.amount,
        "leverage": request.leverage,
        "timestamp": datetime.now().isoformat()
    }

# ----------- Backtest -----------
@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    """백테스트 실행"""
    # 시뮬레이션 결과
    return {
        "success": True,
        "symbol": request.symbol,
        "timeframe": request.timeframe,
        "period": f"{request.start_date} ~ {request.end_date}",
        "results": {
            "total_return": 156.8,
            "win_rate": 68.5,
            "max_drawdown": 12.3,
            "sharpe_ratio": 1.85,
            "trade_count": 48,
            "profit_factor": 2.1
        },
        "trades": []
    }

@app.get("/api/backtest/params")
async def get_backtest_params():
    """백테스트 파라미터 기본값"""
    try:
        from config.parameters import DEFAULT_PARAMS
        return {"params": DEFAULT_PARAMS}
    except Exception:

        return {"params": {
            "macd_fast": 6, "macd_slow": 18, "macd_signal": 7,
            "rsi_period": 14, "atr_period": 14, "atr_mult": 1.25,
            "leverage": 10
        }}

# ----------- Optimization -----------
@app.post("/api/optimization/start")
async def start_optimization(request: OptimizationRequest):
    """최적화 시작"""
    return {
        "job_id": f"OPT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "status": "started",
        "symbol": request.symbol,
        "timeframe": request.timeframe
    }

@app.get("/api/optimization/status/{job_id}")
async def get_optimization_status(job_id: str):
    """최적화 진행 상태"""
    return {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "best_result": {
            "params": {"macd_fast": 5, "macd_slow": 20, "atr_mult": 1.5},
            "return": 245.6,
            "win_rate": 72.3,
            "sharpe": 2.1
        }
    }

# ----------- History -----------
@app.get("/api/history/trades")
async def get_trade_history(
    limit: int = 50,
    exchange: Optional[str] = None,
    symbol: Optional[str] = None
):
    """거래 내역 조회"""
    # 샘플 데이터
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
    return {"timeframes": ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]}

@app.post("/api/data/download")
async def download_data(exchange: str, symbol: str, timeframe: str, days: int = 30):
    """데이터 다운로드 요청"""
    return {
        "status": "started",
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days
    }

# ----------- Auto Trading -----------
@app.post("/api/auto/start")
async def start_auto_trading(config: Dict[str, Any]):
    """자동매매 시작"""
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
