"""
Smart Money Concepts (SMC) Implementation
Based on LuxAlgo's Pine Script logic.

Key Concepts:
1. Swings: Pivot Highs/Lows
2. Structure: BOS (Continuation), CHoCH (Reversal)
3. Order Blocks (OB): Last candle before the impulsive move
4. FVG: Fair Value Gaps
"""

import pandas as pd
import numpy as np

class SMCAnalyzer:
    def __init__(self, df):
        self.df = df.copy()
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.highs = self.df['high'].values
        self.lows = self.df['low'].values
        self.closes = self.df['close'].values
        self.opens = self.df['open'].values
        self.times = self.df['timestamp'].values
        
    def get_swings(self, length=5):
        """
        Identify Swing Highs and Lows (Fractals/Pivots)
        length: Number of bars on left and right to confirm
        """
        df = self.df.copy()
        
        # Vectorized Pivot Detection
        # This is a simplified version. For exact Pine Script match, we need loop or rolling window.
        # Using rolling max/min for efficiency.
        
        # Pivot High: High[i] is max in window [i-length, i+length]
        # Pivot Low: Low[i] is min in window [i-length, i+length]
        
        # Note: This looks ahead 'length' bars. In backtest, we must account for confirmation delay.
        # confirmed_time = time[i + length]
        
        df['is_swing_high'] = False
        df['is_swing_low'] = False
        
        for i in range(length, len(df) - length):
            window_highs = self.highs[i-length : i+length+1]
            window_lows = self.lows[i-length : i+length+1]
            
            if self.highs[i] == np.max(window_highs):
                df.at[i, 'is_swing_high'] = True
                
            if self.lows[i] == np.min(window_lows):
                df.at[i, 'is_swing_low'] = True
                
        return df

    def detect_structure(self, swing_df):
        """
        Detect BOS and CHoCH based on Swings
        """
        structure = []
        trend = 0 # 1: Bullish, -1: Bearish
        
        last_swing_high = None
        last_swing_low = None
        
        # Iterate through bars to simulate real-time detection
        for i in range(len(swing_df)):
            curr_close = self.closes[i]
            curr_high = self.highs[i]
            curr_low = self.lows[i]
            
            # 1. Check for Break of Structure (BOS) / CHoCH
            event = None
            
            if last_swing_high and curr_close > last_swing_high['price']:
                # Break of Resistance
                if trend == 1:
                    event = 'BOS_Bull' # Continuation
                else:
                    event = 'CHoCH_Bull' # Reversal to Bullish
                    trend = 1
                
                # Reset High (consumed) - Optional, depends on logic. Usually we keep tracking new highs.
                # Ideally, we mark the break and look for new swings.
                
            if last_swing_low and curr_close < last_swing_low['price']:
                # Break of Support
                if trend == -1:
                    event = 'BOS_Bear' # Continuation
                else:
                    event = 'CHoCH_Bear' # Reversal to Bearish
                    trend = -1
            
            if event:
                structure.append({
                    'index': i,
                    'time': self.times[i],
                    'type': event,
                    'price': curr_close,
                    'trend': trend
                })
                # Reset swings after break? Or just update trend?
                # In simple SMC, a break invalidates the level.
                if 'Bull' in event:
                    last_swing_high = None # Consumed
                else:
                    last_swing_low = None # Consumed

            # 2. Update Swings (if confirmed at this bar)
            # Swing High detected at i-length, confirmed at i
            # We need to check if 'is_swing_high' is True at i-length
            # But we passed the whole DF. Let's assume we use the pre-calculated column.
            # Wait, 'is_swing_high' at i means the peak is at i. It is confirmed at i+length.
            # So at current bar 'i', we check if 'i-length' was a swing.
            
            # This logic needs to be robust. Let's simplify:
            # We just iterate and update 'last_swing' when a swing is CONFIRMED.
            pass 
            
        return structure

    def get_order_blocks(self, structure_events):
        """
        Identify Order Blocks (OB)
        Bullish OB: Last Bearish candle before Bullish Move (BOS/CHoCH)
        Bearish OB: Last Bullish candle before Bearish Move
        """
        obs = []
        for event in structure_events:
            idx = event['index']
            # Look back from the break point to find the origin of the move
            # Simple logic: Find the lowest point (for Bull move) in the recent leg, 
            # then take the candle before the impulsive move started.
            pass
        return obs

# --- Simplified Logic for Strategy Integration ---
# Instead of full complex SMC, we focus on the core user request:
# "Capture the wave" -> Entry on OB, Exit on Liquidity.

def calculate_smc(df, swing_length=5):
    """
    Returns a DataFrame with SMC signals
    """
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    opens = df['open'].values
    
    # 1. Identify Swings (Confirmed at i)
    # Peak was at i - swing_length
    swing_highs = [] # (price, index)
    swing_lows = []
    
    # Structure
    trend = 0 # 1: Bull, -1: Bear
    last_bos_idx = 0
    
    # Order Blocks
    active_obs = [] # {'type': 'Bull/Bear', 'top': , 'bottom': , 'created_at': }
    
    signals = []
    
    for i in range(swing_length * 2, len(df)):
        # 1. Check for Swing Confirmation
        # Check if i-swing_length was a pivot
        pivot_idx = i - swing_length
        
        is_high = True
        for k in range(pivot_idx - swing_length, pivot_idx + swing_length + 1):
            if highs[k] > highs[pivot_idx]:
                is_high = False
                break
        
        is_low = True
        for k in range(pivot_idx - swing_length, pivot_idx + swing_length + 1):
            if lows[k] < lows[pivot_idx]:
                is_low = False
                break
                
        if is_high:
            swing_highs.append({'price': highs[pivot_idx], 'index': pivot_idx})
            # Check for Bearish Break (CHoCH/BOS) logic is usually price action crossing swing, not swing formation.
            
        if is_low:
            swing_lows.append({'price': lows[pivot_idx], 'index': pivot_idx})

        # 2. Check for Structure Break (Price Action)
        curr_close = closes[i]
        
        # Bullish Break
        if len(swing_highs) > 0:
            last_sh = swing_highs[-1]
            if curr_close > last_sh['price'] and last_sh['index'] > last_bos_idx:
                # BREAK!
                type = 'BOS' if trend == 1 else 'CHoCH'
                trend = 1
                last_bos_idx = i
                
                # Find Bullish OB
                # Origin of this move: Lowest point between last_sh['index'] and i
                # Then find the last bearish candle before that low (or at that low)
                # Simplified: The candle with Lowest Low in the leg
                leg_start_idx = last_sh['index']
                leg_low_val = 99999999
                leg_low_idx = -1
                
                for k in range(leg_start_idx, i):
                    if lows[k] < leg_low_val:
                        leg_low_val = lows[k]
                        leg_low_idx = k
                
                # OB is the candle at leg_low_idx (or the one before it if it was the launch)
                # LuxAlgo logic: "Last Bearish candle before the move"
                # We'll take the candle at the bottom of the leg.
                if leg_low_idx != -1:
                    ob_top = highs[leg_low_idx]
                    ob_bottom = lows[leg_low_idx]
                    active_obs.append({
                        'type': 'Bull', 'top': ob_top, 'bottom': ob_bottom, 
                        'index': leg_low_idx, 'created_at': i
                    })
                    
        # Bearish Break
        if len(swing_lows) > 0:
            last_sl = swing_lows[-1]
            if curr_close < last_sl['price'] and last_sl['index'] > last_bos_idx:
                # BREAK!
                type = 'BOS' if trend == -1 else 'CHoCH'
                trend = -1
                last_bos_idx = i
                
                # Find Bearish OB
                leg_start_idx = last_sl['index']
                leg_high_val = -1
                leg_high_idx = -1
                
                for k in range(leg_start_idx, i):
                    if highs[k] > leg_high_val:
                        leg_high_val = highs[k]
                        leg_high_idx = k
                        
                if leg_high_idx != -1:
                    ob_top = highs[leg_high_idx]
                    ob_bottom = lows[leg_high_idx]
                    active_obs.append({
                        'type': 'Bear', 'top': ob_top, 'bottom': ob_bottom, 
                        'index': leg_high_idx, 'created_at': i
                    })

        # 3. Check for Entry (Retest of OB)
        # We only look at recent OBs (e.g., last 5)
        # Entry: Price touches OB
        
        for ob in active_obs[-3:]: # Check last 3 OBs
            if ob['created_at'] == i: continue # Don't enter on creation bar
            
            if ob['type'] == 'Bull':
                # Price touches OB top (Limit Buy)
                if lows[i] <= ob['top'] and highs[i] >= ob['bottom']:
                    # Valid Retest
                    signals.append({
                        'time': df.iloc[i]['timestamp'],
                        'type': 'Long',
                        'price': ob['top'],
                        'sl': ob['bottom'],
                        'tp': swing_highs[-1]['price'] if len(swing_highs) > 0 else ob['top'] * 1.02
                    })
            elif ob['type'] == 'Bear':
                # Price touches OB bottom (Limit Sell)
                if highs[i] >= ob['bottom'] and lows[i] <= ob['top']:
                    signals.append({
                        'time': df.iloc[i]['timestamp'],
                        'type': 'Short',
                        'price': ob['bottom'],
                        'sl': ob['top'],
                        'tp': swing_lows[-1]['price'] if len(swing_lows) > 0 else ob['bottom'] * 0.98
                    })
                    
    return signals
