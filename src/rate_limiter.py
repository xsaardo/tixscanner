"""
Rate limiting implementation for TixScanner API clients.

This module provides rate limiting functionality to ensure API usage
stays within provider limits and implements proper backoff strategies.
"""

import sqlite3
import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from .database import get_connection, get_db_transaction

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for API requests with persistent storage.
    
    Tracks API usage over time windows and prevents exceeding rate limits.
    Uses SQLite database for persistence across application restarts.
    """
    
    def __init__(self, max_requests: int, time_window: int, 
                 db_path: Optional[str] = None, service_name: str = "default"):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds (e.g., 86400 for daily limit)
            db_path: Database path (uses default if None)
            service_name: Service identifier for multiple rate limiters
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.db_path = db_path
        self.service_name = service_name
        
        # Initialize database table
        self._init_rate_limit_table()
        
        logger.debug(f"Rate limiter initialized: {max_requests} requests per {time_window}s")
    
    def _init_rate_limit_table(self) -> None:
        """Initialize the rate limiting table in the database."""
        try:
            with get_db_transaction(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rate_limits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        request_time TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create index for efficient queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rate_limits_service_time 
                    ON rate_limits (service_name, request_time)
                """)
                
        except Exception as e:
            logger.error(f"Failed to initialize rate limit table: {e}")
    
    def can_make_request(self) -> bool:
        """
        Check if a new request can be made without exceeding rate limits.
        
        Returns:
            True if request can be made, False otherwise
        """
        try:
            current_usage = self.get_current_usage()
            can_proceed = current_usage < self.max_requests
            
            logger.debug(f"Rate limit check: {current_usage}/{self.max_requests} requests used")
            return can_proceed
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Fail open - allow request if we can't check
            return True
    
    def record_request(self) -> None:
        """Record that a request was made."""
        try:
            with get_db_transaction(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO rate_limits (service_name, request_time)
                    VALUES (?, ?)
                """, (self.service_name, datetime.now()))
                
            logger.debug(f"Recorded API request for {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to record API request: {e}")
    
    def get_current_usage(self) -> int:
        """
        Get current usage within the time window.
        
        Returns:
            Number of requests made in the current time window
        """
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.time_window)
            
            with get_connection(self.db_path) as conn:
                result = conn.execute("""
                    SELECT COUNT(*) FROM rate_limits 
                    WHERE service_name = ? AND request_time >= ?
                """, (self.service_name, cutoff_time.isoformat())).fetchone()
                
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"Failed to get current usage: {e}")
            return 0
    
    def get_remaining_requests(self) -> int:
        """
        Get number of requests remaining in current time window.
        
        Returns:
            Number of requests that can still be made
        """
        current_usage = self.get_current_usage()
        return max(0, self.max_requests - current_usage)
    
    def get_reset_time(self) -> datetime:
        """
        Get when the rate limit window will reset.
        
        Returns:
            DateTime when the oldest request in current window expires
        """
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.time_window)
            
            with get_connection(self.db_path) as conn:
                result = conn.execute("""
                    SELECT MIN(request_time) FROM rate_limits 
                    WHERE service_name = ? AND request_time >= ?
                """, (self.service_name, cutoff_time.isoformat())).fetchone()
                
                if result and result[0]:
                    oldest_request = datetime.fromisoformat(result[0])
                    return oldest_request + timedelta(seconds=self.time_window)
                else:
                    # No requests in window, reset time is now
                    return datetime.now()
                    
        except Exception as e:
            logger.error(f"Failed to get reset time: {e}")
            return datetime.now()
    
    def wait_if_needed(self, max_wait: int = 300) -> bool:
        """
        Wait if necessary to avoid rate limiting.
        
        Args:
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if we can proceed, False if max wait exceeded
        """
        if self.can_make_request():
            return True
        
        reset_time = self.get_reset_time()
        wait_seconds = (reset_time - datetime.now()).total_seconds()
        
        if wait_seconds <= 0:
            return True
        
        if wait_seconds > max_wait:
            logger.warning(f"Rate limit wait time ({wait_seconds:.0f}s) exceeds max wait ({max_wait}s)")
            return False
        
        logger.info(f"Rate limit reached, waiting {wait_seconds:.0f} seconds")
        time.sleep(wait_seconds)
        return True
    
    def cleanup_old_records(self) -> int:
        """
        Clean up old rate limit records outside the time window.
        
        Returns:
            Number of records cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.time_window * 2)  # Keep some extra
            
            with get_db_transaction(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM rate_limits 
                    WHERE service_name = ? AND request_time < ?
                """, (self.service_name, cutoff_time.isoformat()))
                
                deleted_count = cursor.rowcount
                
            if deleted_count > 0:
                logger.debug(f"Cleaned up {deleted_count} old rate limit records")
                
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old rate limit records: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with rate limiting statistics
        """
        try:
            current_usage = self.get_current_usage()
            remaining = self.get_remaining_requests()
            reset_time = self.get_reset_time()
            
            # Get request history for the last hour
            hour_ago = datetime.now() - timedelta(hours=1)
            
            with get_connection(self.db_path) as conn:
                hourly_usage = conn.execute("""
                    SELECT COUNT(*) FROM rate_limits 
                    WHERE service_name = ? AND request_time >= ?
                """, (self.service_name, hour_ago.isoformat())).fetchone()[0]
            
            return {
                'service_name': self.service_name,
                'max_requests': self.max_requests,
                'time_window_seconds': self.time_window,
                'current_usage': current_usage,
                'remaining_requests': remaining,
                'usage_percentage': round((current_usage / self.max_requests) * 100, 1),
                'reset_time': reset_time.isoformat(),
                'hourly_usage': hourly_usage
            }
            
        except Exception as e:
            logger.error(f"Failed to get rate limiter stats: {e}")
            return {'error': str(e)}
    
    def reset(self) -> None:
        """
        Reset the rate limiter by clearing all records.
        
        WARNING: This will allow unlimited requests until new limits are hit.
        """
        try:
            with get_db_transaction(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM rate_limits WHERE service_name = ?
                """, (self.service_name,))
                
                deleted_count = cursor.rowcount
                
            logger.warning(f"Rate limiter reset: cleared {deleted_count} records for {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to reset rate limiter: {e}")


class ExponentialBackoff:
    """
    Exponential backoff utility for handling API errors and retries.
    
    Implements exponential backoff with jitter for resilient API calls.
    """
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, 
                 backoff_factor: float = 2.0, jitter: bool = True):
        """
        Initialize exponential backoff.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Multiplier for each retry
            jitter: Whether to add random jitter to delays
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.attempt = 0
    
    def get_delay(self) -> float:
        """
        Get the delay for the current attempt.
        
        Returns:
            Delay in seconds
        """
        delay = min(self.base_delay * (self.backoff_factor ** self.attempt), self.max_delay)
        
        if self.jitter:
            import random
            # Add up to 25% jitter
            jitter_amount = delay * 0.25 * random.random()
            delay += jitter_amount
        
        return delay
    
    def wait(self) -> None:
        """Wait for the calculated delay and increment attempt counter."""
        delay = self.get_delay()
        logger.debug(f"Exponential backoff: waiting {delay:.2f}s (attempt {self.attempt + 1})")
        time.sleep(delay)
        self.attempt += 1
    
    def reset(self) -> None:
        """Reset the attempt counter."""
        self.attempt = 0