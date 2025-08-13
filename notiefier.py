import os
import logging
from typing import Dict
from datetime import datetime, timedelta
import telegram

class TelegramNotifier:
    """
    Handles sending notifications to a Telegram chat.
    """
    def __init__(self, config: Dict):
        self.logger = logging.getLogger(__name__)
        self.config = config.get('telegram', {})
        self.strategy_config = config.get('strategy', {})
        self.enabled = self.config.get('enabled', False)
        
        if not self.enabled:
            self.logger.info("Telegram notifier is disabled in config.")
            return
            
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.cooldown_hours = self.strategy_config.get('signal_cooldown_hours', 3)
        self._last_signal_time = {} 

        if not self.token or not self.chat_id:
            self.logger.error("Telegram token or chat_id not set. Disabling notifier.")
            self.enabled = False
            return
        
        try:
            self.bot = telegram.Bot(token=self.token)
            self.logger.info("TelegramNotifier initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram Bot: {e}")
            self.enabled = False

    def is_cooldown_active(self, symbol: str, direction: str) -> bool:
        key = f"{symbol}_{direction}"
        last_time = self._last_signal_time.get(key)
        if not last_time:
            return False
        
        cooldown_period = timedelta(hours=self.cooldown_hours)
        return datetime.now() < last_time + cooldown_period

    def update_cooldown(self, symbol: str, direction: str):
        key = f"{symbol}_{direction}"
        self._last_signal_time[key] = datetime.now()
        self.logger.info(f"Cooldown timer started for {key}.")

    def send_signal(self, signal: Dict):
        if not self.enabled:
            return

        direction_emoji = "🟢" if signal['direction'] == 'LONG' else "🔴"
        price = signal['entry_price']
        precision = 2 if price > 100 else 4 if price > 1 else 6

        message = (
            f"📡 **Sinyal {signal['direction']}** {direction_emoji}\n\n"
            f"**Pair**: `{signal['symbol']}`\n"
            f"**TF**: `8H/4H/1H/15m` | **Skor**: `{signal['score']:.1f}/10`\n\n"
            f"**Entry**: `{signal['entry_price']:.{precision}f}`\n"
            f"**SL**: `{signal['sl_price']:.{precision}f}`\n"
            f"**TP1**: `{signal['tp1_price']:.{precision}f}`\n"
            f"**TP2**: `{signal['tp2_price']:.{precision}f}`\n\n"
            f"**R:R (TP1)**: `1:{signal['rr_ratio']:.2f}`\n\n"
            f"**Konfluensi**:\n"
            f" - " + "\n - ".join(signal['confluence_points']) + "\n\n"
            f"**Timestamp (WIB)**: `{signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}`"
        )

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            self.logger.info(f"Successfully sent signal for {signal['symbol']} to Telegram.")
        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
