"""
Scheduling system for TixScanner price monitoring.

This module provides scheduling functionality for:
- Regular price checks
- Daily summary emails
- Database cleanup tasks
"""

import logging
import time
from datetime import datetime, time as dt_time
from typing import Optional, Callable, Dict, Any
from threading import Thread, Event

from .price_monitor import PriceMonitor
from .git_backup import GitDatabaseBackup

logger = logging.getLogger(__name__)


class MonitoringScheduler:
    """
    Scheduler for automated price monitoring tasks.
    
    Handles periodic price checks, daily summaries, and maintenance tasks.
    """
    
    def __init__(self, price_monitor: PriceMonitor):
        """
        Initialize scheduler.
        
        Args:
            price_monitor: PriceMonitor instance to schedule
        """
        self.price_monitor = price_monitor
        self.is_running = False
        self.stop_event = Event()
        self.thread = None
        
        # Default schedule configuration
        self.price_check_interval = 2  # hours
        self.daily_summary_time = dt_time(9, 0)  # 9:00 AM
        self.cleanup_interval_days = 7  # Run cleanup weekly
        self.backup_time = dt_time(0, 0)  # Midnight for database backup

        self._last_price_check = None
        self._last_summary_date = None
        self._last_cleanup_date = None
        self._last_backup_date = None

        # Initialize git backup system
        self.git_backup = GitDatabaseBackup()

        # Try to restore database on startup (for Codespaces)
        try:
            self.git_backup.restore_database_from_git()
        except Exception as e:
            logger.warning(f"Database restore attempt failed: {e}")
        
        logger.info("Monitoring scheduler initialized")
    
    def configure(self, price_check_interval: int = 2,
                 daily_summary_time: dt_time = dt_time(9, 0),
                 cleanup_interval_days: int = 7,
                 backup_time: dt_time = dt_time(0, 0)) -> None:
        """
        Configure scheduling parameters.
        
        Args:
            price_check_interval: Hours between price checks
            daily_summary_time: Time to send daily summary
            cleanup_interval_days: Days between database cleanup
        """
        self.price_check_interval = price_check_interval
        self.daily_summary_time = daily_summary_time
        self.cleanup_interval_days = cleanup_interval_days
        self.backup_time = backup_time

        logger.info(f"Scheduler configured: price checks every {price_check_interval}h, "
                   f"daily summary at {daily_summary_time}, "
                   f"cleanup every {cleanup_interval_days} days, "
                   f"backup at {backup_time}")
    
    def start(self) -> None:
        """Start the monitoring scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting monitoring scheduler")
        self.is_running = True
        self.stop_event.clear()
        
        self.thread = Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("Monitoring scheduler started")
    
    def stop(self) -> None:
        """Stop the monitoring scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping monitoring scheduler")
        self.is_running = False
        self.stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        
        logger.info("Monitoring scheduler stopped")
    
    def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        while not self.stop_event.wait(timeout=60):  # Check every minute
            try:
                current_time = datetime.now()
                
                # Check if price check is due
                if self._should_check_prices(current_time):
                    self._run_price_check()

                # Check if daily summary is due
                if self._should_send_summary(current_time):
                    self._send_daily_summary()

                # Check if database backup is due
                if self._should_backup_database(current_time):
                    self._backup_database()

                # Check if cleanup is due
                if self._should_run_cleanup(current_time):
                    self._run_cleanup()
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
        
        logger.info("Scheduler loop stopped")
    
    def _should_check_prices(self, current_time: datetime) -> bool:
        """Determine if price check should run."""
        if not self._last_price_check:
            return True
        
        hours_since_check = (current_time - self._last_price_check).total_seconds() / 3600
        return hours_since_check >= self.price_check_interval
    
    def _should_send_summary(self, current_time: datetime) -> bool:
        """Determine if daily summary should be sent."""
        current_date = current_time.date()
        current_time_only = current_time.time()
        
        # Check if we haven't sent today and it's time
        if (self._last_summary_date != current_date and 
            current_time_only >= self.daily_summary_time):
            return True
        
        return False
    
    def _should_backup_database(self, current_time: datetime) -> bool:
        """Determine if database backup should run."""
        current_date = current_time.date()
        current_time_only = current_time.time()

        # Check if we haven't backed up today and it's time
        if (self._last_backup_date != current_date and
                current_time_only >= self.backup_time):
            return True

        return False

    def _should_run_cleanup(self, current_time: datetime) -> bool:
        """Determine if database cleanup should run."""
        if not self._last_cleanup_date:
            return True

        days_since_cleanup = (current_time.date() - self._last_cleanup_date).days
        return days_since_cleanup >= self.cleanup_interval_days
    
    def _run_price_check(self) -> None:
        """Run price check task."""
        logger.info("Running scheduled price check")
        
        try:
            results = self.price_monitor.check_all_prices()
            self._last_price_check = datetime.now()
            
            logger.info(f"Price check completed: {results['prices_checked']} prices checked, "
                       f"{results['alerts_sent']} alerts sent")
            
        except Exception as e:
            logger.error(f"Error during scheduled price check: {e}")
    
    def _send_daily_summary(self) -> None:
        """Send daily summary email."""
        logger.info("Sending scheduled daily summary")
        
        try:
            success = self.price_monitor.send_daily_summary()
            if success:
                self._last_summary_date = datetime.now().date()
                logger.info("Daily summary sent successfully")
            else:
                logger.error("Failed to send daily summary")
                
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
    
    def _backup_database(self) -> None:
        """Run database backup task."""
        logger.info("Running scheduled database backup")

        try:
            result = self.git_backup.backup_database()
            if result['success']:
                self._last_backup_date = datetime.now().date()
                logger.info(f"Database backup completed: {result['message']}")
            else:
                logger.error(f"Database backup failed: {result['message']}")

        except Exception as e:
            logger.error(f"Error during database backup: {e}")

    def _run_cleanup(self) -> None:
        """Run database cleanup task."""
        logger.info("Running scheduled database cleanup")

        try:
            deleted_count = self.price_monitor.cleanup_old_data()
            self._last_cleanup_date = datetime.now().date()

            logger.info(f"Database cleanup completed: {deleted_count} records deleted")

        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
    
    def run_once(self) -> Dict[str, Any]:
        """
        Run all monitoring tasks once (for testing/manual execution).
        
        Returns:
            Dictionary with execution results
        """
        logger.info("Running all monitoring tasks once")
        
        results = {
            'price_check': None,
            'daily_summary': False,
            'backup': None,
            'cleanup': 0,
            'timestamp': datetime.now()
        }
        
        try:
            # Run price check
            results['price_check'] = self.price_monitor.check_all_prices()
            
            # Send daily summary
            results['daily_summary'] = self.price_monitor.send_daily_summary()

            # Backup database
            backup_result = self.git_backup.backup_database()
            results['backup'] = backup_result

            # Run cleanup
            results['cleanup'] = self.price_monitor.cleanup_old_data()
            
            logger.info("All monitoring tasks completed successfully")
            
        except Exception as e:
            logger.error(f"Error running monitoring tasks: {e}")
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get scheduler status.
        
        Returns:
            Dictionary with scheduler status information
        """
        status = {
            'is_running': self.is_running,
            'price_check_interval': self.price_check_interval,
            'daily_summary_time': self.daily_summary_time.strftime('%H:%M'),
            'cleanup_interval_days': self.cleanup_interval_days,
            'backup_time': self.backup_time.strftime('%H:%M'),
            'last_price_check': self._last_price_check,
            'last_summary_date': self._last_summary_date,
            'last_backup_date': self._last_backup_date,
            'last_cleanup_date': self._last_cleanup_date,
            'next_price_check': self._calculate_next_price_check(),
            'next_summary': self._calculate_next_summary(),
            'next_backup': self._calculate_next_backup(),
            'next_cleanup': self._calculate_next_cleanup()
        }

        # Add git backup status
        try:
            backup_status = self.git_backup.get_backup_status()
            status['git_backup'] = backup_status
        except Exception as e:
            logger.warning(f"Failed to get git backup status: {e}")
            status['git_backup'] = {'error': str(e)}

        return status
    
    def _calculate_next_price_check(self) -> Optional[datetime]:
        """Calculate next scheduled price check time."""
        if not self._last_price_check:
            return datetime.now()
        
        from datetime import timedelta
        return self._last_price_check + timedelta(hours=self.price_check_interval)
    
    def _calculate_next_summary(self) -> datetime:
        """Calculate next scheduled summary time."""
        current = datetime.now()
        today_summary = datetime.combine(current.date(), self.daily_summary_time)
        
        if self._last_summary_date == current.date() or current.time() >= self.daily_summary_time:
            # Already sent today or missed today's time, schedule for tomorrow
            from datetime import timedelta
            return today_summary + timedelta(days=1)
        else:
            return today_summary
    
    def _calculate_next_backup(self) -> datetime:
        """Calculate next scheduled backup time."""
        current = datetime.now()
        today_backup = datetime.combine(current.date(), self.backup_time)

        if self._last_backup_date == current.date() or current.time() >= self.backup_time:
            # Already backed up today or missed today's time, schedule for tomorrow
            from datetime import timedelta
            return today_backup + timedelta(days=1)
        else:
            return today_backup

    def _calculate_next_cleanup(self) -> datetime:
        """Calculate next scheduled cleanup time."""
        current = datetime.now()

        if not self._last_cleanup_date:
            return current

        from datetime import timedelta
        return datetime.combine(self._last_cleanup_date, dt_time()) + timedelta(days=self.cleanup_interval_days)