import logging
from typing import Dict, Optional
import pandas as pd

class RiskManager:
    """
    Calculates Stop Loss (SL) and Take Profit (TP) levels for a given signal.
    """
    def __init__(self, config: Dict):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.min_rr = config['strategy']['min_rr_ratio']
        self.atr_multiplier = config['risk']['atr_buffer_multiplier']
        self.atr_col = f"ATRr_{config['indicators']['atr']['length']}"

    def calculate_sl_tp(self, signal: Dict, entry_df: pd.DataFrame) -> Optional[Dict]:
        """
        Calculates SL/TP and validates the risk-to-reward ratio.
        """
        direction = signal['direction']
        entry_price = signal['entry_price']
        fib_levels = signal['fib_levels']

        if 'error' in fib_levels:
            self.logger.warning(f"Cannot calculate SL/TP: {fib_levels['error']}")
            return None

        atr_buffer = entry_df.iloc[-1][self.atr_col] * self.atr_multiplier
        
        if direction == 'LONG':
            sl_price = fib_levels['low'] - atr_buffer
            tp1 = fib_levels['retracement']['0.618']
            tp2 = fib_levels['high'] # Target the swing high as TP2
            if entry_price > fib_levels['high']: # Breakout case
                tp1 = fib_levels['extension']['1.272']
                tp2 = fib_levels['extension']['1.618']
        else: # SHORT
            sl_price = fib_levels['high'] + atr_buffer
            tp1 = fib_levels['retracement']['0.618']
            tp2 = fib_levels['low'] # Target the swing low as TP2
            if entry_price < fib_levels['low']: # Breakdown case
                tp1 = fib_levels['extension']['1.272']
                tp2 = fib_levels['extension']['1.618']

        risk = abs(entry_price - sl_price)
        reward = abs(tp1 - entry_price)

        if risk == 0:
            self.logger.warning("Risk is zero, cannot calculate R:R. Discarding signal.")
            return None
            
        rr_ratio = reward / risk

        if rr_ratio < self.min_rr:
            self.logger.info(f"Signal for {signal['symbol']} discarded. R:R ({rr_ratio:.2f}) is below minimum ({self.min_rr}).")
            return None
        
        self.logger.info(f"Signal R:R is valid ({rr_ratio:.2f}). SL: {sl_price:.4f}, TP1: {tp1:.4f}")

        signal['sl_price'] = sl_price
        signal['tp1_price'] = tp1
        signal['tp2_price'] = tp2
        signal['rr_ratio'] = rr_ratio
        
        return signal
