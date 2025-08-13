import logging
import ccxt
import pandas as pd
from typing import Optional, Dict

class DataClient:
    """
    Handles all communication with the cryptocurrency exchange via CCXT.
    """
    def __init__(self, config: Dict):
        self.logger = logging.getLogger(__name__)
        exchange_id = config.get('id', 'binance')
        exchange_class = getattr(ccxt, exchange_id)
        
        self.exchange = exchange_class({
            'rateLimit': config.get('rate_limit_aware', True),
            'options': {
                'defaultType': config.get('market_type', 'spot'),
            },
        })
        self.logger.info(f"DataClient initialized for exchange: {self.exchange.id}")

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """
        Fetches OHLCV data for a given symbol and timeframe.
        """
        try:
            self.logger.debug(f"Fetching {limit} bars of {symbol} on {timeframe} timeframe...")
            if not self.exchange.has['fetchOHLCV']:
                self.logger.error(f"Exchange {self.exchange.id} does not support fetchOHLCV.")
                return None

            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                self.logger.warning(f"No OHLCV data returned for {symbol} on {timeframe}.")
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            self.logger.debug(f"Successfully fetched {len(df)} bars for {symbol} on {timeframe}.")
            return df

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in fetch_ohlcv: {e}", exc_info=True)
        
        return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetches the current ticker price for a symbol.
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            self.logger.error(f"Could not fetch current price for {symbol}: {e}")
            return None
