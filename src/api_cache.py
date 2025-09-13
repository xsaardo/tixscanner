"""
API response caching implementation for TixScanner.

This module provides caching functionality for API responses to reduce
redundant API calls and improve performance while respecting cache policies.
"""

import json
import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List
from pathlib import Path

from .database import get_connection, get_db_transaction

logger = logging.getLogger(__name__)


class APICache:
    """
    API response cache with SQLite backend.
    
    Provides caching functionality for API responses with configurable
    expiration times and cache management utilities.
    """
    
    def __init__(self, cache_duration_minutes: int = 30, 
                 db_path: Optional[str] = None, max_cache_size: int = 1000):
        """
        Initialize API cache.
        
        Args:
            cache_duration_minutes: Default cache duration in minutes
            db_path: Database path (uses default if None)
            max_cache_size: Maximum number of cached items
        """
        self.cache_duration_minutes = cache_duration_minutes
        self.db_path = db_path
        self.max_cache_size = max_cache_size
        
        # Initialize cache table
        self._init_cache_table()
        
        logger.debug(f"API cache initialized with {cache_duration_minutes}min duration")
    
    def _init_cache_table(self) -> None:
        """Initialize the cache table in the database."""
        try:
            with get_db_transaction(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cache_key TEXT UNIQUE NOT NULL,
                        cache_value TEXT NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 1
                    )
                """)
                
                # Create indexes for performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cache_key 
                    ON api_cache (cache_key)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cache_expires 
                    ON api_cache (expires_at)
                """)
                
        except Exception as e:
            logger.error(f"Failed to initialize cache table: {e}")
    
    def _generate_cache_key(self, key: str) -> str:
        """
        Generate a consistent cache key hash.
        
        Args:
            key: Original cache key
            
        Returns:
            Hashed cache key
        """
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        try:
            cache_key = self._generate_cache_key(key)
            
            with get_connection(self.db_path) as conn:
                row = conn.execute("""
                    SELECT cache_value, expires_at FROM api_cache 
                    WHERE cache_key = ? AND expires_at > ?
                """, (cache_key, datetime.now().isoformat())).fetchone()
                
                if row:
                    # Update access statistics
                    conn.execute("""
                        UPDATE api_cache 
                        SET accessed_at = ?, access_count = access_count + 1
                        WHERE cache_key = ?
                    """, (datetime.now().isoformat(), cache_key))
                    
                    # Deserialize cached value
                    cached_data = json.loads(row['cache_value'])
                    logger.debug(f"Cache hit for key: {key[:50]}...")
                    return cached_data
                
            logger.debug(f"Cache miss for key: {key[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached value: {e}")
            return None
    
    def set(self, key: str, value: Any, 
            duration_minutes: Optional[int] = None) -> bool:
        """
        Set cached value.
        
        Args:
            key: Cache key
            value: Value to cache
            duration_minutes: Cache duration (uses default if None)
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(key)
            duration = duration_minutes or self.cache_duration_minutes
            expires_at = datetime.now() + timedelta(minutes=duration)
            
            # Serialize value
            cache_value = json.dumps(value, default=str)
            
            with get_db_transaction(self.db_path) as conn:
                # Insert or replace cache entry
                conn.execute("""
                    INSERT OR REPLACE INTO api_cache 
                    (cache_key, cache_value, expires_at, created_at, accessed_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    cache_key, cache_value, expires_at.isoformat(),
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
                
            logger.debug(f"Cached value for key: {key[:50]}... (expires: {expires_at})")
            
            # Clean up if cache is getting too large
            if self._get_cache_size() > self.max_cache_size:
                self._cleanup_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache value: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete cached value by key.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        try:
            cache_key = self._generate_cache_key(key)
            
            with get_db_transaction(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM api_cache WHERE cache_key = ?
                """, (cache_key,))
                
                deleted = cursor.rowcount > 0
                
            if deleted:
                logger.debug(f"Deleted cached value for key: {key[:50]}...")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete cached value: {e}")
            return False
    
    def clear(self) -> int:
        """
        Clear all cached values.
        
        Returns:
            Number of items cleared
        """
        try:
            with get_db_transaction(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM api_cache")
                cleared_count = cursor.rowcount
                
            logger.info(f"Cleared {cleared_count} cached items")
            return cleared_count
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0
    
    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of expired items removed
        """
        try:
            with get_db_transaction(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM api_cache WHERE expires_at <= ?
                """, (datetime.now().isoformat(),))
                
                expired_count = cursor.rowcount
                
            if expired_count > 0:
                logger.debug(f"Cleaned up {expired_count} expired cache entries")
                
            return expired_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache entries: {e}")
            return 0
    
    def _cleanup_cache(self) -> None:
        """Clean up cache when it gets too large."""
        try:
            # First remove expired entries
            self.cleanup_expired()
            
            current_size = self._get_cache_size()
            if current_size <= self.max_cache_size:
                return
            
            # Remove oldest entries that haven't been accessed recently
            items_to_remove = current_size - self.max_cache_size + 100  # Remove extra for buffer
            
            with get_db_transaction(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM api_cache 
                    WHERE id IN (
                        SELECT id FROM api_cache 
                        ORDER BY accessed_at ASC 
                        LIMIT ?
                    )
                """, (items_to_remove,))
                
                removed_count = cursor.rowcount
                
            logger.info(f"Cache cleanup: removed {removed_count} old entries")
            
        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
    
    def _get_cache_size(self) -> int:
        """Get current cache size."""
        try:
            with get_connection(self.db_path) as conn:
                result = conn.execute("SELECT COUNT(*) FROM api_cache").fetchone()
                return result[0] if result else 0
        except Exception:
            return 0
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            with get_connection(self.db_path) as conn:
                # Get basic stats
                stats_query = """
                    SELECT 
                        COUNT(*) as total_items,
                        COUNT(CASE WHEN expires_at > ? THEN 1 END) as active_items,
                        COUNT(CASE WHEN expires_at <= ? THEN 1 END) as expired_items,
                        AVG(access_count) as avg_access_count,
                        MAX(access_count) as max_access_count
                    FROM api_cache
                """
                
                now = datetime.now().isoformat()
                stats = conn.execute(stats_query, (now, now)).fetchone()
                
                # Get recent activity
                hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                recent_activity = conn.execute("""
                    SELECT COUNT(*) FROM api_cache WHERE created_at >= ?
                """, (hour_ago,)).fetchone()[0]
                
                return {
                    'total_items': stats['total_items'],
                    'active_items': stats['active_items'],
                    'expired_items': stats['expired_items'],
                    'cache_hit_potential': round((stats['active_items'] / max(stats['total_items'], 1)) * 100, 1),
                    'avg_access_count': round(stats['avg_access_count'] or 0, 1),
                    'max_access_count': stats['max_access_count'] or 0,
                    'recent_additions': recent_activity,
                    'max_cache_size': self.max_cache_size,
                    'cache_duration_minutes': self.cache_duration_minutes
                }
                
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'error': str(e)}
    
    def get_cache_entries(self, limit: int = 50) -> List[Dict]:
        """
        Get recent cache entries for debugging.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of cache entry dictionaries
        """
        try:
            with get_connection(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT 
                        cache_key, expires_at, created_at, accessed_at, access_count,
                        LENGTH(cache_value) as size_bytes
                    FROM api_cache 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,)).fetchall()
                
                entries = []
                for row in rows:
                    entries.append({
                        'cache_key': row['cache_key'][:16] + '...',  # Truncate for display
                        'expires_at': row['expires_at'],
                        'created_at': row['created_at'],
                        'accessed_at': row['accessed_at'],
                        'access_count': row['access_count'],
                        'size_bytes': row['size_bytes'],
                        'is_expired': row['expires_at'] <= datetime.now().isoformat()
                    })
                
                return entries
                
        except Exception as e:
            logger.error(f"Failed to get cache entries: {e}")
            return []
    
    def is_cached(self, key: str) -> bool:
        """
        Check if a key is cached and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if cached and valid, False otherwise
        """
        return self.get(key) is not None
    
    def get_expiry_time(self, key: str) -> Optional[datetime]:
        """
        Get expiry time for a cached key.
        
        Args:
            key: Cache key
            
        Returns:
            Expiry datetime or None if not cached
        """
        try:
            cache_key = self._generate_cache_key(key)
            
            with get_connection(self.db_path) as conn:
                row = conn.execute("""
                    SELECT expires_at FROM api_cache WHERE cache_key = ?
                """, (cache_key,)).fetchone()
                
                if row:
                    return datetime.fromisoformat(row['expires_at'])
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get expiry time: {e}")
            return None