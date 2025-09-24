#!/usr/bin/env python3
"""
TixScanner - Ticket Price Tracking Application

A single-user Python application that tracks concert ticket prices via 
Ticketmaster API and sends email notifications when prices drop below 
specified thresholds.
"""

import logging
import sys
import argparse
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


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='TixScanner - Ticket Price Tracking Application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run continuous monitoring (default)
  python main.py --mode check       # Single price check only
  python main.py --mode summary     # Send daily summary only
        """
    )

    parser.add_argument(
        '--mode',
        choices=['continuous', 'check', 'summary'],
        default='continuous',
        help='Operation mode (default: continuous)'
    )

    return parser.parse_args()


def run_single_check(config: 'ConfigManager', price_monitor: 'PriceMonitor', logger: logging.Logger) -> None:
    """Run a single price check without scheduling."""
    logger.info("Running single price check...")
    results = price_monitor.check_all_prices()
    logger.info(f"Price check complete: {results['prices_checked']} prices checked, "
               f"{results['alerts_sent']} alerts sent")


def run_daily_summary(config: 'ConfigManager', email_client: 'EmailClient', logger: logging.Logger) -> None:
    """Send daily summary email only."""
    logger.info("Sending daily summary...")
    try:
        success = email_client.send_daily_summary()
        if success:
            logger.info("Daily summary sent successfully")
        else:
            logger.error("Failed to send daily summary")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error sending daily summary: {e}")
        sys.exit(1)


def run_continuous_monitoring(config: 'ConfigManager', price_monitor: 'PriceMonitor', logger: logging.Logger) -> None:
    """Run continuous monitoring with scheduler."""
    import time
    from src.scheduler import MonitoringScheduler

    # Run initial check
    logger.info("Running initial price check...")
    results = price_monitor.check_all_prices()
    logger.info(f"Initial check complete: {results['prices_checked']} prices checked, "
               f"{results['alerts_sent']} alerts sent")

    # Start scheduler for continuous monitoring
    scheduler = MonitoringScheduler(price_monitor)
    scheduler.start()
    logger.info("Monitoring scheduler started - running continuously")

    # Keep running until interrupted
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Stopping scheduler...")
        scheduler.stop()


def main() -> None:
    """Main entry point for the TixScanner application."""
    args = parse_arguments()
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info(f"TixScanner starting up in {args.mode} mode...")

    try:
        # Import core components
        from src.config_manager import ConfigManager
        from src.price_monitor import PriceMonitor
        from src.email_client import EmailClient

        # Load configuration
        config = ConfigManager()

        # Initialize components
        email_client = EmailClient()

        if args.mode == 'summary':
            # For summary mode, we only need email client
            run_daily_summary(config, email_client, logger)
        else:
            # For check and continuous modes, we need price monitor
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

            if args.mode == 'check':
                run_single_check(config, price_monitor, logger)
            elif args.mode == 'continuous':
                run_continuous_monitoring(config, price_monitor, logger)

        logger.info(f"TixScanner {args.mode} mode completed successfully")

    except KeyboardInterrupt:
        logger.info("Shutting down TixScanner...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()