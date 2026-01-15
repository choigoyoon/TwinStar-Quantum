# storage/local_trade_db.py
"""
로컬 거래 데이터베이스 (Local Trade DB, LTDB)
- 모든 체결 내역(executions)을 저장
- FIFO(선입선출) 기반의 실현 손익(PnL) 계산
- 수수료(Commissions) 추적
- 업비트, 빗썸, Lighter 등 API 지원이 부족한 거래소용
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class Execution:
    """개별 체결 내역"""
    exchange: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    price: float
    amount: float
    fee: float = 0.0
    fee_currency: str = 'USDT'
    order_id: str = ""
    timestamp: str = ""
    id: Optional[int] = None

@dataclass
class ClosedTrade:
    """청산된 거래 정보 (PnL 포함)"""
    exchange: str
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    entry_price: float
    exit_price: float
    amount: float
    pnl: float
    pnl_pct: float
    entry_time: str
    exit_time: str
    commission: float
    id: Optional[int] = None

class LocalTradeDB:
    """SQLite 기반 로컬 거래 데이터베이스"""
    
    def __init__(self, db_path: str = 'data/local_trades.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """테이블 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            # 1. 체결 내역 테이블 (모든 BUY/SELL)
            c.execute('''
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exchange TEXT,
                    symbol TEXT,
                    side TEXT,
                    price REAL,
                    amount REAL,
                    fee REAL,
                    fee_currency TEXT,
                    order_id TEXT,
                    timestamp TEXT,
                    is_closed INTEGER DEFAULT 0,
                    remaining_amount REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 2. 청산 거래 테이블 (PnL 결과물)
            c.execute('''
                CREATE TABLE IF NOT EXISTS closed_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exchange TEXT,
                    symbol TEXT,
                    side TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    amount REAL,
                    pnl REAL,
                    pnl_pct REAL,
                    entry_time TEXT,
                    exit_time TEXT,
                    commission REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            
    def add_execution(self, exe: Execution):
        """새로운 체결 내역 추가"""
        if not exe.timestamp:
            exe.timestamp = datetime.now().isoformat()
            
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO executions (
                    exchange, symbol, side, price, amount, 
                    fee, fee_currency, order_id, timestamp, remaining_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                exe.exchange.lower(), exe.symbol.upper(), exe.side.upper(),
                exe.price, exe.amount, exe.fee, exe.fee_currency, 
                exe.order_id, exe.timestamp, exe.amount
            ))
            conn.commit()
            logging.info(f"[LTDB] Execution saved: {exe.exchange} {exe.symbol} {exe.side} {exe.amount} @ {exe.price}")
            
    def get_open_executions(self, exchange: str, symbol: str, side: str) -> List[Dict[str, Any]]:
        """청산되지 않은 체결 리스트 조회 (FIFO용)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('''
                SELECT * FROM executions 
                WHERE exchange = ? AND symbol = ? AND side = ? AND is_closed = 0
                ORDER BY timestamp ASC
            ''', (exchange.lower(), symbol.upper(), side.upper()))
            return [dict(row) for row in c.fetchall()]

    def record_closed_trade(self, trade: ClosedTrade):
        """청산 결과 저장"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO closed_trades (
                    exchange, symbol, side, entry_price, exit_price,
                    amount, pnl, pnl_pct, entry_time, exit_time, commission
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.exchange.lower(), trade.symbol.upper(), trade.side.upper(),
                trade.entry_price, trade.exit_price, trade.amount,
                trade.pnl, trade.pnl_pct, trade.entry_time, trade.exit_time, trade.commission
            ))
            conn.commit()

    def calculate_pnl_fifo(self, exchange: str, symbol: str, exit_price: float, exit_amount: float, exit_side: str, exit_time: str, fee: float = 0.0) -> Optional[ClosedTrade]:
        """FIFO 방식으로 PnL 계산 및 업데이트"""
        entry_side = 'SELL' if exit_side.upper() == 'BUY' else 'BUY'
        opens = self.get_open_executions(exchange, symbol, entry_side)
        
        if not opens:
            logging.warning(f"[LTDB] No matching open executions found for {symbol} {entry_side}")
            return None
            
        total_pnl = 0.0
        total_entry_value = 0.0
        remaining_to_close = exit_amount
        actual_closed_amount = 0.0
        earliest_entry_time = ""
        total_commission = fee
        
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            for exe in opens:
                if remaining_to_close <= 0:
                    break
                    
                exe_id = exe['id']
                exe_price = exe['price']
                exe_remaining = exe['remaining_amount']
                exe_commission = exe['fee']
                
                if not earliest_entry_time:
                    earliest_entry_time = exe['timestamp']
                
                amount_to_process = min(exe_remaining, remaining_to_close)
                
                # PnL 계산
                if exit_side.upper() == 'SELL': # Long Exit
                    trade_pnl = (exit_price - exe_price) * amount_to_process
                else: # Short Exit
                    trade_pnl = (exe_price - exit_price) * amount_to_process
                
                total_pnl += trade_pnl
                total_entry_value += (exe_price * amount_to_process)
                actual_closed_amount += amount_to_process
                remaining_to_close -= amount_to_process
                total_commission += (exe_commission * (amount_to_process / exe['amount']))
                
                # DB 업데이트
                new_remaining = exe_remaining - amount_to_process
                is_closed = 1 if new_remaining < 0.00000001 else 0
                
                c.execute('''
                    UPDATE executions SET remaining_amount = ?, is_closed = ? WHERE id = ?
                ''', (new_remaining, is_closed, exe_id))
            
            conn.commit()
            
        if actual_closed_amount > 0:
            avg_entry_price = total_entry_value / actual_closed_amount
            pnl_pct = (total_pnl / total_entry_value * 100) if total_entry_value > 0 else 0
            
            trade = ClosedTrade(
                exchange=exchange,
                symbol=symbol,
                side='LONG' if exit_side.upper() == 'SELL' else 'SHORT',
                entry_price=avg_entry_price,
                exit_price=exit_price,
                amount=actual_closed_amount,
                pnl=total_pnl,
                pnl_pct=pnl_pct,
                entry_time=earliest_entry_time,
                exit_time=exit_time,
                commission=total_commission
            )
            self.record_closed_trade(trade)
            return trade
            
        return None

    def get_summary(self, exchange: Optional[str] = None) -> Dict[str, Any]:
        """통계 요약"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            query = "SELECT COUNT(*) as cnt, SUM(pnl) as total_pnl, SUM(commission) as total_fee FROM closed_trades"
            params = []
            if exchange:
                query += " WHERE exchange = ?"
                params.append(exchange.lower())
                
            c.execute(query, params)
            row = c.fetchone()
            
            return {
                'total_trades': row['cnt'] or 0,
                'total_pnl': row['total_pnl'] or 0.0,
                'total_fee': row['total_fee'] or 0.0,
                'net_pnl': (row['total_pnl'] or 0.0) - (row['total_fee'] or 0.0)
            }

    def get_all_closed_trades(self, limit: int = 200) -> List[Dict[str, Any]]:
        """모든 청산 거래 내역 조회"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('''
                SELECT * FROM closed_trades 
                ORDER BY exit_time DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in c.fetchall()]

# 싱글톤 인스턴스
_db_instance = None

def get_local_db() -> LocalTradeDB:
    global _db_instance
    if _db_instance is None:
        _db_instance = LocalTradeDB()
    return _db_instance
