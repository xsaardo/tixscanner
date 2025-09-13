"""
API monitoring and logging utilities for TixScanner.

This module provides comprehensive monitoring of API usage, performance,
and error tracking for better observability and debugging.
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import time

from .database import get_connection, get_db_transaction

logger = logging.getLogger(__name__)


@dataclass
class APIMetrics:
    """Data class for API metrics."""
    endpoint: str
    method: str
    status_code: int
    response_time: float
    request_size: int
    response_size: int
    error_message: Optional[str] = None
    cache_hit: bool = False


class APIMonitor:
    """
    API monitoring and metrics collection.
    
    Tracks API usage, performance metrics, error rates, and provides
    analytics for optimizing API usage and troubleshooting issues.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize API monitor.
        
        Args:
            db_path: Database path (uses default if None)
        """
        self.db_path = db_path
        self._init_monitoring_tables()
        
        logger.debug("API monitor initialized")
    
    def _init_monitoring_tables(self) -> None:
        """Initialize monitoring tables in the database."""
        try:
            with get_db_transaction(self.db_path) as conn:
                # API requests log table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        endpoint TEXT NOT NULL,
                        method TEXT NOT NULL,
                        status_code INTEGER NOT NULL,
                        response_time REAL NOT NULL,
                        request_size INTEGER DEFAULT 0,
                        response_size INTEGER DEFAULT 0,
                        error_message TEXT,
                        cache_hit BOOLEAN DEFAULT FALSE,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # API errors table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_errors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        endpoint TEXT NOT NULL,
                        error_type TEXT NOT NULL,
                        error_message TEXT,
                        status_code INTEGER,
                        retry_count INTEGER DEFAULT 0,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Performance metrics table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        metric_unit TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_api_requests_timestamp 
                    ON api_requests (timestamp)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_api_requests_endpoint 
                    ON api_requests (endpoint)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_api_errors_timestamp 
                    ON api_errors (timestamp)
                """)
                
        except Exception as e:
            logger.error(f"Failed to initialize monitoring tables: {e}")
    
    def log_request(self, metrics: APIMetrics) -> None:
        """
        Log an API request with metrics.
        
        Args:
            metrics: API metrics data
        """
        try:
            with get_db_transaction(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO api_requests 
                    (endpoint, method, status_code, response_time, request_size, 
                     response_size, error_message, cache_hit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.endpoint,
                    metrics.method,
                    metrics.status_code,
                    metrics.response_time,
                    metrics.request_size,
                    metrics.response_size,
                    metrics.error_message,
                    metrics.cache_hit
                ))
                
            logger.debug(f"Logged API request: {metrics.method} {metrics.endpoint} - {metrics.status_code}")
            
        except Exception as e:
            logger.error(f"Failed to log API request: {e}")
    
    def log_error(self, endpoint: str, error_type: str, error_message: str,
                  status_code: Optional[int] = None, retry_count: int = 0) -> None:
        """
        Log an API error.
        
        Args:
            endpoint: API endpoint that failed
            error_type: Type of error (timeout, auth, etc.)
            error_message: Error message
            status_code: HTTP status code (if applicable)
            retry_count: Number of retries attempted
        """
        try:
            with get_db_transaction(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO api_errors 
                    (endpoint, error_type, error_message, status_code, retry_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (endpoint, error_type, error_message, status_code, retry_count))
                
            logger.debug(f"Logged API error: {error_type} on {endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to log API error: {e}")
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = "") -> None:
        """
        Log a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
        """
        try:
            with get_db_transaction(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO api_performance (metric_name, metric_value, metric_unit)
                    VALUES (?, ?, ?)
                """, (metric_name, value, unit))
                
            logger.debug(f"Logged performance metric: {metric_name} = {value} {unit}")
            
        except Exception as e:
            logger.error(f"Failed to log performance metric: {e}")
    
    def get_usage_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get API usage statistics for the specified time period.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with usage statistics
        """
        try:
            since_time = datetime.now() - timedelta(hours=hours)
            
            with get_connection(self.db_path) as conn:
                # Basic usage stats
                usage_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_requests,
                        COUNT(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 END) as successful_requests,
                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_requests,
                        COUNT(CASE WHEN cache_hit = 1 THEN 1 END) as cache_hits,
                        AVG(response_time) as avg_response_time,
                        MAX(response_time) as max_response_time,
                        MIN(response_time) as min_response_time
                    FROM api_requests 
                    WHERE timestamp >= ?
                """, (since_time.isoformat(),)).fetchone()
                
                # Endpoint breakdown
                endpoint_stats = conn.execute("""
                    SELECT 
                        endpoint,
                        COUNT(*) as request_count,
                        AVG(response_time) as avg_response_time
                    FROM api_requests 
                    WHERE timestamp >= ?
                    GROUP BY endpoint
                    ORDER BY request_count DESC
                """, (since_time.isoformat(),)).fetchall()
                
                # Error breakdown
                error_stats = conn.execute("""
                    SELECT 
                        error_type,
                        COUNT(*) as error_count
                    FROM api_errors 
                    WHERE timestamp >= ?
                    GROUP BY error_type
                    ORDER BY error_count DESC
                """, (since_time.isoformat(),)).fetchall()
                
                total_requests = usage_stats['total_requests']
                
                return {
                    'time_period_hours': hours,
                    'total_requests': total_requests,
                    'successful_requests': usage_stats['successful_requests'],
                    'error_requests': usage_stats['error_requests'],
                    'success_rate': round((usage_stats['successful_requests'] / max(total_requests, 1)) * 100, 1),
                    'cache_hits': usage_stats['cache_hits'],
                    'cache_hit_rate': round((usage_stats['cache_hits'] / max(total_requests, 1)) * 100, 1),
                    'avg_response_time': round(usage_stats['avg_response_time'] or 0, 3),
                    'max_response_time': round(usage_stats['max_response_time'] or 0, 3),
                    'min_response_time': round(usage_stats['min_response_time'] or 0, 3),
                    'endpoints': [dict(row) for row in endpoint_stats],
                    'errors': [dict(row) for row in error_stats]
                }
                
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {'error': str(e)}
    
    def get_error_rate(self, hours: int = 24) -> float:
        """
        Get current error rate percentage.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Error rate as percentage
        """
        try:
            since_time = datetime.now() - timedelta(hours=hours)
            
            with get_connection(self.db_path) as conn:
                stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_requests,
                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_requests
                    FROM api_requests 
                    WHERE timestamp >= ?
                """, (since_time.isoformat(),)).fetchone()
                
                total = stats['total_requests']
                errors = stats['error_requests']
                
                return round((errors / max(total, 1)) * 100, 2)
                
        except Exception as e:
            logger.error(f"Failed to get error rate: {e}")
            return 0.0
    
    def get_avg_response_time(self, hours: int = 24) -> float:
        """
        Get average response time.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Average response time in seconds
        """
        try:
            since_time = datetime.now() - timedelta(hours=hours)
            
            with get_connection(self.db_path) as conn:
                result = conn.execute("""
                    SELECT AVG(response_time) FROM api_requests 
                    WHERE timestamp >= ? AND status_code >= 200 AND status_code < 300
                """, (since_time.isoformat(),)).fetchone()
                
                return round(result[0] or 0, 3)
                
        except Exception as e:
            logger.error(f"Failed to get average response time: {e}")
            return 0.0
    
    def get_recent_errors(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """
        Get recent API errors for troubleshooting.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of errors to return
            
        Returns:
            List of recent error dictionaries
        """
        try:
            since_time = datetime.now() - timedelta(hours=hours)
            
            with get_connection(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT 
                        endpoint, error_type, error_message, status_code,
                        retry_count, timestamp
                    FROM api_errors 
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (since_time.isoformat(), limit)).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return []
    
    def is_api_healthy(self, hours: int = 1) -> bool:
        """
        Check if API is currently healthy based on recent metrics.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            True if API appears healthy, False otherwise
        """
        try:
            error_rate = self.get_error_rate(hours)
            avg_response_time = self.get_avg_response_time(hours)
            
            # Consider API healthy if:
            # - Error rate is below 10%
            # - Average response time is below 5 seconds
            return error_rate < 10.0 and avg_response_time < 5.0
            
        except Exception as e:
            logger.error(f"Failed to check API health: {e}")
            return False
    
    def cleanup_old_metrics(self, days: int = 30) -> int:
        """
        Clean up old monitoring data.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of records cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            total_deleted = 0
            
            with get_db_transaction(self.db_path) as conn:
                # Clean up API requests
                cursor = conn.execute("""
                    DELETE FROM api_requests WHERE timestamp < ?
                """, (cutoff_time.isoformat(),))
                total_deleted += cursor.rowcount
                
                # Clean up API errors
                cursor = conn.execute("""
                    DELETE FROM api_errors WHERE timestamp < ?
                """, (cutoff_time.isoformat(),))
                total_deleted += cursor.rowcount
                
                # Clean up performance metrics
                cursor = conn.execute("""
                    DELETE FROM api_performance WHERE timestamp < ?
                """, (cutoff_time.isoformat(),))
                total_deleted += cursor.rowcount
                
            if total_deleted > 0:
                logger.info(f"Cleaned up {total_deleted} old monitoring records")
                
            return total_deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
            return 0
    
    def generate_usage_report(self, hours: int = 24) -> str:
        """
        Generate a formatted usage report.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Formatted report string
        """
        try:
            stats = self.get_usage_stats(hours)
            
            report_lines = [
                f"📊 API Usage Report ({hours}h period)",
                f"=" * 40,
                f"Total Requests: {stats['total_requests']}",
                f"Success Rate: {stats['success_rate']}%",
                f"Cache Hit Rate: {stats['cache_hit_rate']}%",
                f"Avg Response Time: {stats['avg_response_time']}s",
                ""
            ]
            
            # Add endpoint breakdown
            if stats['endpoints']:
                report_lines.append("Top Endpoints:")
                for endpoint in stats['endpoints'][:5]:
                    report_lines.append(
                        f"  {endpoint['endpoint']}: {endpoint['request_count']} req "
                        f"({endpoint['avg_response_time']:.3f}s avg)"
                    )
                report_lines.append("")
            
            # Add error breakdown
            if stats['errors']:
                report_lines.append("Error Types:")
                for error in stats['errors']:
                    report_lines.append(f"  {error['error_type']}: {error['error_count']} errors")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate usage report: {e}")
            return f"Error generating report: {e}"


class RequestLogger:
    """
    Context manager for logging API requests with automatic metrics collection.
    """
    
    def __init__(self, monitor: APIMonitor, endpoint: str, method: str = "GET"):
        """
        Initialize request logger.
        
        Args:
            monitor: APIMonitor instance
            endpoint: API endpoint being called
            method: HTTP method
        """
        self.monitor = monitor
        self.endpoint = endpoint
        self.method = method
        self.start_time = None
        self.metrics = None
    
    def __enter__(self):
        """Start timing the request."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log the request metrics."""
        if self.start_time:
            response_time = time.time() - self.start_time
            
            if self.metrics:
                self.metrics.response_time = response_time
                self.monitor.log_request(self.metrics)
            else:
                # Log basic metrics if no detailed metrics were set
                basic_metrics = APIMetrics(
                    endpoint=self.endpoint,
                    method=self.method,
                    status_code=500 if exc_type else 200,
                    response_time=response_time,
                    request_size=0,
                    response_size=0,
                    error_message=str(exc_val) if exc_val else None
                )
                self.monitor.log_request(basic_metrics)
    
    def set_metrics(self, status_code: int, request_size: int = 0, 
                   response_size: int = 0, cache_hit: bool = False,
                   error_message: Optional[str] = None) -> None:
        """
        Set detailed metrics for the request.
        
        Args:
            status_code: HTTP status code
            request_size: Request size in bytes
            response_size: Response size in bytes
            cache_hit: Whether this was a cache hit
            error_message: Error message if any
        """
        self.metrics = APIMetrics(
            endpoint=self.endpoint,
            method=self.method,
            status_code=status_code,
            response_time=0,  # Will be set in __exit__
            request_size=request_size,
            response_size=response_size,
            error_message=error_message,
            cache_hit=cache_hit
        )