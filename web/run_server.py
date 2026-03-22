"""
TwinStar Quantum Web Server
백엔드 API + 프론트엔드 정적 파일 서빙
"""
import os
import sys
import io
import uvicorn
from pathlib import Path

# UTF-8 출력 설정 (Windows용)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# 메인 앱
app = FastAPI(title="TwinStar Quantum Web")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프론트엔드 경로
frontend_path = Path(__file__).parent / "frontend"

# ============= Models =============
class TradeRequest(BaseModel):
    exchange: str
    symbol: str
    side: str
    amount: float
    leverage: int = 1

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    params: Optional[Dict[str, Any]] = None

# ============= API Routes =============

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/dashboard/status")
async def get_dashboard_status():
    return {
        "balance": {"total": 10000.0, "available": 8500.0, "in_position": 1500.0},
        "positions": [],
        "pnl": {"daily": 125.50, "weekly": 450.00, "monthly": 1200.00},
        "active_bots": 0
    }

@app.get("/api/exchanges")
async def get_exchanges():
    return {"exchanges": ["bybit", "binance", "okx", "bitget", "bingx", "upbit", "bithumb"]}

@app.get("/api/symbols/{exchange}")
async def get_symbols(exchange: str):
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    return {"exchange": exchange, "symbols": symbols}

@app.post("/api/trade")
async def execute_trade(request: TradeRequest):
    return {
        "success": True,
        "order_id": f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "exchange": request.exchange,
        "symbol": request.symbol,
        "side": request.side,
        "amount": request.amount,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    return {
        "success": True,
        "symbol": request.symbol,
        "results": {
            "total_return": 156.8,
            "win_rate": 68.5,
            "max_drawdown": 12.3,
            "sharpe_ratio": 1.85,
            "trade_count": 48,
            "profit_factor": 2.1
        }
    }

@app.get("/api/history/trades")
async def get_trade_history():
    return {"trades": [
        {"id": 1, "datetime": "2026-01-13 10:30:00", "exchange": "bybit", 
         "symbol": "BTCUSDT", "side": "Long", "pnl": 125.50, "pnl_pct": 2.5},
        {"id": 2, "datetime": "2026-01-13 09:15:00", "exchange": "bybit",
         "symbol": "ETHUSDT", "side": "Short", "pnl": -45.20, "pnl_pct": -0.9},
        {"id": 3, "datetime": "2026-01-12 16:45:00", "exchange": "binance",
         "symbol": "SOLUSDT", "side": "Long", "pnl": 89.30, "pnl_pct": 1.8},
    ]}

@app.get("/api/auto/status")
async def get_auto_status():
    return {"running": False, "uptime": 0, "trades_today": 0, "pnl_today": 0.0}

# ============= Frontend =============

@app.get("/")
async def serve_frontend():
    return FileResponse(frontend_path / "index.html")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 TwinStar Quantum Web Server")
    print("=" * 60)
    print(f"📂 Project: {project_root}")
    print(f"🌐 URL: http://0.0.0.0:8000")
    print("=" * 60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
