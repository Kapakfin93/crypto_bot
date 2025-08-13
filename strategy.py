import logging
from typing import Dict, Optional
import pandas as pd

class StrategyEvaluator:
    """
    Evaluates analysis, scores confluence, and generates a trade signal.
    """
    def __init__(self, config: Dict):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.min_score = config['strategy']['min_confluence_score']
        self.tfs = config['timeframes']

    def _get_col_names(self) -> Dict:
        """Helper to get indicator column names from config."""
        p = self.config['indicators']
        return {
            'ema_fast': f"EMA_{p['ema_fast']['length']}",
            'ema_slow': f"EMA_{p['ema_slow']['length']}",
            'smma': f"SMMA_{p['smma']['length']}",
            'macd': f"MACD_{p['macd']['fast']}_{p['macd']['slow']}_{p['macd']['signal']}",
            'macds': f"MACDs_{p['macd']['fast']}_{p['macd']['slow']}_{p['macd']['signal']}",
            'stoch_k': f"STOCHk_{p['stochastic']['k']}_{p['stochastic']['d']}_{p['stochastic']['smooth_k']}",
            'stoch_d': f"STOCHd_{p['stochastic']['k']}_{p['stochastic']['d']}_{p['stochastic']['smooth_k']}",
        }

    def evaluate(self, analysis: Dict) -> Optional[Dict]:
        """
        Main evaluation function.
        """
        bias = analysis['bias_8h']
        if bias == 'NEUTRAL':
            self.logger.info("Evaluation skipped: 8H bias is NEUTRAL.")
            return None

        score = 0.0
        confluence_points = []
        cols = self._get_col_names()
        latest = analysis['latest_candles']
        
        # 1. Score 8H Bias (Max 4 points)
        bias_8h_data = latest[self.tfs['bias']]
        if bias == 'BULLISH':
            score += 2.0; confluence_points.append("8H Bias: Bullish")
            if bias_8h_data[cols['ema_fast']] > bias_8h_data[cols['ema_slow']]:
                score += 1.0; confluence_points.append("8H EMA 50/200: Golden")
            if bias_8h_data['close'] > bias_8h_data[cols['smma']]:
                score += 1.0; confluence_points.append("8H Price > SMMA28")
        elif bias == 'BEARISH':
            score += 2.0; confluence_points.append("8H Bias: Bearish")
            if bias_8h_data[cols['ema_fast']] < bias_8h_data[cols['ema_slow']]:
                score += 1.0; confluence_points.append("8H EMA 50/200: Death")
            if bias_8h_data['close'] < bias_8h_data[cols['smma']]:
                score += 1.0; confluence_points.append("8H Price < SMMA28")

        # 2. Score 4H Confirmation (Max 3 points)
        conf_4h_data = latest[self.tfs['confirmation']]
        if bias == 'BULLISH' and (conf_4h_data['close'] - conf_4h_data['low']) > 0.6 * (conf_4h_data['high'] - conf_4h_data['low']):
            score += 2.0; confluence_points.append("4H Rejection: Bullish Wick")
        elif bias == 'BEARISH' and (conf_4h_data['high'] - conf_4h_data['close']) > 0.6 * (conf_4h_data['high'] - conf_4h_data['low']):
            score += 2.0; confluence_points.append("4H Rejection: Bearish Wick")
        
        if bias == 'BULLISH' and conf_4h_data[cols['macd']] > conf_4h_data[cols['macds']]:
            score += 1.0; confluence_points.append("4H MACD: Bullish")
        elif bias == 'BEARISH' and conf_4h_data[cols['macd']] < conf_4h_data[cols['macds']]:
            score += 1.0; confluence_points.append("4H MACD: Bearish")
            
        # 3. Score 1H Pattern (Max 1 point) - Simplified
        pattern_1h_data = latest[self.tfs['pattern']]
        if (bias == 'BULLISH' and pattern_1h_data['close'] > pattern_1h_data['open']) or \
           (bias == 'BEARISH' and pattern_1h_data['close'] < pattern_1h_data['open']):
             score += 1.0; confluence_points.append(f"1H Pattern: {bias.title()} Candle")

        # 4. Score 15m Entry Trigger (Max 2 points)
        entry_15m_data = latest[self.tfs['entry']]
        prev_15m_data = analysis['data'][self.tfs['entry']].iloc[-3]
        
        is_bull_trigger = (entry_15m_data[cols['stoch_k']] > entry_15m_data[cols['stoch_d']] and
                           prev_15m_data[cols['stoch_k']] <= prev_15m_data[cols['stoch_d']] and
                           entry_15m_data[cols['macd']] > entry_15m_data[cols['macds']])
                           
        is_bear_trigger = (entry_15m_data[cols['stoch_k']] < entry_15m_data[cols['stoch_d']] and
                           prev_15m_data[cols['stoch_k']] >= prev_15m_data[cols['stoch_d']] and
                           entry_15m_data[cols['macd']] < entry_15m_data[cols['macds']])

        if (bias == 'BULLISH' and is_bull_trigger) or (bias == 'BEARISH' and is_bear_trigger):
            score += 2.0; confluence_points.append(f"15m Trigger: Stoch & MACD {bias.title()} Cross")

        self.logger.info(f"Final confluence score for {analysis['symbol']} ({bias}): {score:.2f}/10")

        if score >= self.min_score:
            direction = "LONG" if bias == "BULLISH" else "SHORT"
            self.logger.info(f"Score threshold met! Generating {direction} signal.")
            return {
                'symbol': analysis['symbol'], 'direction': direction,
                'entry_price': analysis['current_price'], 'score': score,
                'confluence_points': confluence_points, 'fib_levels': analysis['fib_levels_8h'],
                'timestamp': pd.Timestamp.now(tz=self.config['telegram']['timezone'])
            }
        return None
