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
        # TODO: Import and initialize core components
        # TODO: Load configuration
        # TODO: Start price monitoring scheduler
        logger.info("TixScanner initialized successfully")
        
    except KeyboardInterrupt:
        logger.info("Shutting down TixScanner...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()