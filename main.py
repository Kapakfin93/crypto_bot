import os
import time
import logging
import argparse
from datetime import datetime

import yaml
from dotenv import load_dotenv

from data_client import DataClient
from mtf_logic import MTFAnalyzer
from strategy import StrategyEvaluator
from risk import RiskManager
from notifier import TelegramNotifier
from utils import setup_logging

def run_bot(pair_symbol: str, config: dict):
    """
    Main function to run the trading bot logic for a given pair.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting analysis for symbol: {pair_symbol}")

    try:
        # 1. Initialize Components
        data_client = DataClient(config['exchange'])
        mtf_analyzer = MTFAnalyzer(data_client, config)
        strategy_evaluator = StrategyEvaluator(config)
        risk_manager = RiskManager(config)
        notifier = TelegramNotifier(config)

        # 2. Perform Multi-Timeframe Analysis
        analysis_result = mtf_analyzer.analyze(pair_symbol)

        if not analysis_result or not analysis_result.get('is_valid', False):
            logger.info(f"Analysis for {pair_symbol} did not yield a valid setup. Skipping.")
            return

        # 3. Evaluate Strategy and Score Confluence
        trade_signal = strategy_evaluator.evaluate(analysis_result)

        if not trade_signal:
            logger.info(f"No valid trade signal generated for {pair_symbol} based on current strategy rules.")
            return

        # 4. Calculate Risk/Reward
        entry_df = analysis_result['data'][config['timeframes']['entry']]
        final_signal = risk_manager.calculate_sl_tp(trade_signal, entry_df)

        if not final_signal:
            logger.warning(f"Signal for {pair_symbol} discarded due to invalid R:R or SL/TP calculation.")
            return
            
        # 5. Send Notification
        if notifier.is_cooldown_active(pair_symbol, final_signal['direction']):
            logger.info(f"Signal for {pair_symbol} is on cooldown. Skipping notification.")
        else:
            logger.info(f"✅ Valid signal found for {pair_symbol}! Sending notification...")
            notifier.send_signal(final_signal)
            notifier.update_cooldown(pair_symbol, final_signal['direction'])

    except Exception as e:
        logger.error(f"An unexpected error occurred during the analysis for {pair_symbol}: {e}", exc_info=True)


def main():
    """
    Entry point of the script.
    """
    load_dotenv()
    setup_logging()
    logger = logging.getLogger(__name__)

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    parser = argparse.ArgumentParser(description="MTF Crypto Trading Bot")
    parser.add_argument('--pair', type=str, default=config['exchange']['default_symbol'],
                        help=f"The trading pair to analyze (e.g., BTC/USDT). Default: {config['exchange']['default_symbol']}")
    args = parser.parse_args()

    if config['telegram']['enabled']:
        if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
            logger.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env file.")
            return
            
    run_interval_seconds = config['operation'].get('run_interval_minutes', 15) * 60
    logger.info(f"Bot started. Running analysis every {run_interval_seconds / 60} minutes.")
    
    while True:
        try:
            run_bot(args.pair, config)
        except Exception as e:
            logger.critical(f"A critical error occurred in the main loop: {e}", exc_info=True)
        
        logger.info(f"Analysis complete. Waiting for {run_interval_seconds / 60} minutes until the next run.")
        time.sleep(run_interval_seconds)


if __name__ == "__main__":
    main()
