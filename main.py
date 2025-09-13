#!/usr/bin/env python3
"""
TixScanner - Ticket Price Tracking Application

A single-user Python application that tracks concert ticket prices via 
Ticketmaster API and sends email notifications when prices drop below 
specified thresholds.
"""

import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def setup_logging() -> None:
    """Set up logging configuration."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "tixscanner.log"),
            logging.StreamHandler()
        ]
    )


def main() -> None:
    """Main entry point for the TixScanner application."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("TixScanner starting up...")
    
    try:
        # Import core components
        from src.config_manager import ConfigManager
        from src.price_monitor import PriceMonitor
        from src.scheduler import MonitoringScheduler
        from src.email_client import EmailClient
        
        # Load configuration
        config = ConfigManager()
        
        # Initialize components
        email_client = EmailClient()
        price_monitor = PriceMonitor(
            api_key=config.get_ticketmaster_api_key(),
            email_client=email_client
        )
        
        # Configure monitoring parameters
        price_monitor.configure(
            min_price_drop_percent=config.get_monitoring_config().get('minimum_price_drop_percent', 10.0),
            check_frequency_hours=config.get_monitoring_config().get('check_frequency_hours', 2)
        )
        
        # Test setup before starting
        test_results = price_monitor.test_monitoring_setup()
        if not test_results['ready_for_monitoring']:
            logger.error("Monitoring setup test failed. Please check configuration.")
            logger.error(f"Test results: {test_results}")
            sys.exit(1)
        
        logger.info("All systems ready for monitoring")
        
        # Run monitoring tasks once
        logger.info("Running initial price check...")
        results = price_monitor.check_all_prices()
        logger.info(f"Initial check complete: {results['prices_checked']} prices checked, "
                   f"{results['alerts_sent']} alerts sent")
        
        # Optional: Start scheduler for continuous monitoring
        # Uncomment these lines for continuous monitoring:
        # scheduler = MonitoringScheduler(price_monitor)
        # scheduler.start()
        # logger.info("Monitoring scheduler started - running continuously")
        # 
        # # Keep running until interrupted
        # try:
        #     while True:
        #         time.sleep(60)
        # except KeyboardInterrupt:
        #     logger.info("Stopping scheduler...")
        #     scheduler.stop()
        
        logger.info("TixScanner run completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Shutting down TixScanner...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()