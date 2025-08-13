import pandas as pd
import pandas_ta as ta
from typing import Dict

def calculate_indicators(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """
    Calculates all required technical indicators and appends them to the DataFrame.
    """
    p = config['indicators'] 

    df.ta.macd(fast=p['macd']['fast'], slow=p['macd']['slow'], signal=p['macd']['signal'], append=True)
    df.ta.stochrsi(length=p['stoch_rsi']['length'], rsi_length=p['stoch_rsi']['length'], 
                   k=p['stoch_rsi']['smooth_k'], d=p['stoch_rsi']['smooth_d'], append=True)
    df.ta.stoch(k=p['stochastic']['k'], d=p['stochastic']['d'], smooth_k=p['stochastic']['smooth_k'], append=True)
    df.ta.smma(length=p['smma']['length'], append=True)
    df.ta.ema(length=p['ema_fast']['length'], append=True)
    df.ta.ema(length=p['ema_slow']['length'], append=True)
    df.ta.ema(length=p['ema_trend_short']['length'], append=True)
    df.ta.ema(length=p['ema_trend_long']['length'], append=True)
    df.ta.atr(length=p['atr']['length'], append=True)

    # Simplified fractal-based swing detection for Fibonacci
    df['swing_high'] = df['high'][(df['high'].shift(2) < df['high']) &
                                  (df['high'].shift(1) < df['high']) &
                                  (df['high'].shift(-1) < df['high']) &
                                  (df['high'].shift(-2) < df['high'])]
    
    df['swing_low'] = df['low'][(df['low'].shift(2) > df['low']) &
                                (df['low'].shift(1) > df['low']) &
                                (df['low'].shift(-1) > df['low']) &
                                (df['low'].shift(-2) > df['low'])]
    return df

def get_fibonacci_levels(df: pd.DataFrame) -> Dict:
    """
    Identifies the most recent swing high and low to calculate Fibonacci levels.
    """
    last_swing_high_price = df['swing_high'].dropna().iloc[-1] if not df['swing_high'].dropna().empty else None
    last_swing_high_time = df['swing_high'].dropna().index[-1] if not df['swing_high'].dropna().empty else None
    
    last_swing_low_price = df['swing_low'].dropna().iloc[-1] if not df['swing_low'].dropna().empty else None
    last_swing_low_time = df['swing_low'].dropna().index[-1] if not df['swing_low'].dropna().empty else None

    if not all([last_swing_high_price, last_swing_low_price]):
        return {'error': 'Not enough swing points to determine Fibonacci levels.'}

    if last_swing_high_time > last_swing_low_time:
        high_point, low_point, trend = last_swing_high_price, last_swing_low_price, 'up'
    else:
        high_point, low_point, trend = last_swing_high_price, last_swing_low_price, 'down'

    diff = high_point - low_point
    
    levels = {
        'retracement': {
            '0.382': high_point - 0.382 * diff,
            '0.5': high_point - 0.5 * diff,
            '0.618': high_point - 0.618 * diff,
        },
        'extension': {
            '1.272': high_point + 0.272 * diff if trend == 'up' else low_point - 0.272 * diff,
            '1.618': high_point + 0.618 * diff if trend == 'up' else low_point - 0.618 * diff,
        },
        'high': high_point, 'low': low_point, 'trend': trend
    }
    return levels
