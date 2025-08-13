import logging
import sys

def setup_logging():
    """
    Configures the root logger for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Uncomment the line below to also log to a file
            # logging.FileHandler("trading_bot.log")
        ]
    )
    # Suppress verbose logging from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
