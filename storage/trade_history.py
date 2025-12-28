"""
거래 내역 및 수익 통계 시스템
- 거래 내역 저장/조회
- 일별/주별/월별 수익 통계
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class TradeRecord:
    """거래 기록"""
    id: int = 0
    symbol: str = ""
    exchange: str = ""
    side: str = ""  # LONG/SHORT
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    entry_time: str = ""
    exit_time: str = ""
    reason: str = ""  # STOP_LOSS, TAKE_PROFIT, TRAILING, MANUAL


# [FIX] EXE 호환 경로 처리
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)

# 데이터베이스 경로
DB_PATH = os.path.join(BASE_DIR, 'data', 'trades.db')


class TradeHistory:
    """거래 내역 관리"""
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """데이터베이스 초기화"""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                exchange TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                pnl REAL,
                pnl_percent REAL,
                entry_time TEXT,
                exit_time TEXT,
                reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_trade(self, trade: TradeRecord) -> int:
        """거래 추가"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO trades (
                symbol, exchange, side, entry_price, exit_price,
                quantity, pnl, pnl_percent, entry_time, exit_time, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.symbol, trade.exchange, trade.side,
            trade.entry_price, trade.exit_price, trade.quantity,
            trade.pnl, trade.pnl_percent, trade.entry_time, trade.exit_time,
            trade.reason
        ))
        
        trade_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    def get_trades(self, days: int = 30, exchange: str = None) -> List[TradeRecord]:
        """거래 내역 조회"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        if exchange:
            c.execute('''
                SELECT * FROM trades
                WHERE exit_time >= ? AND exchange = ?
                ORDER BY exit_time DESC
            ''', (since, exchange))
        else:
            c.execute('''
                SELECT * FROM trades
                WHERE exit_time >= ?
                ORDER BY exit_time DESC
            ''', (since,))
        
        rows = c.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            trades.append(TradeRecord(
                id=row[0], symbol=row[1], exchange=row[2], side=row[3],
                entry_price=row[4], exit_price=row[5], quantity=row[6],
                pnl=row[7], pnl_percent=row[8], entry_time=row[9],
                exit_time=row[10], reason=row[11]
            ))
        
        return trades
    
    def get_daily_stats(self, days: int = 30) -> List[dict]:
        """일별 통계"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        c.execute('''
            SELECT 
                DATE(exit_time) as date,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl
            FROM trades
            WHERE exit_time >= ?
            GROUP BY DATE(exit_time)
            ORDER BY date ASC
        ''', (since,))
        
        rows = c.fetchall()
        conn.close()
        
        stats = []
        for row in rows:
            date, trades, wins, total_pnl = row
            win_rate = (wins / trades * 100) if trades > 0 else 0
            stats.append({
                'date': date,
                'trades': trades,
                'wins': wins,
                'win_rate': win_rate,
                'pnl': total_pnl or 0
            })
        
        return stats
    
    def get_summary(self) -> dict:
        """전체 통계 요약"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl,
                MAX(pnl) as best_trade,
                MIN(pnl) as worst_trade
            FROM trades
        ''')
        
        row = c.fetchone()
        conn.close()
        
        total, wins, pnl, best, worst = row
        win_rate = (wins / total * 100) if total and total > 0 else 0
        
        return {
            'total_trades': total or 0,
            'wins': wins or 0,
            'losses': (total or 0) - (wins or 0),
            'win_rate': win_rate,
            'total_pnl': pnl or 0,
            'best_trade': best or 0,
            'worst_trade': worst or 0
        }


# 싱글톤
_history = None

def get_trade_history() -> TradeHistory:
    global _history
    if _history is None:
        _history = TradeHistory()
    return _history


# 테스트
if __name__ == "__main__":
    history = get_trade_history()
    
    # 테스트 데이터 추가
    trade = TradeRecord(
        symbol="BTCUSDT",
        exchange="bybit",
        side="LONG",
        entry_price=98000,
        exit_price=99500,
        quantity=0.05,
        pnl=75.0,
        pnl_percent=1.53,
        entry_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        exit_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        reason="TRAILING"
    )
    
    trade_id = history.add_trade(trade)
    print(f"거래 추가됨: ID {trade_id}")
    
    # 통계 확인
    summary = history.get_summary()
    print("\n=== 전체 통계 ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
