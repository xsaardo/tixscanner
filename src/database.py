"""
Database connection management and schema initialization for TixScanner.

This module handles SQLite database connections, schema creation, and 
provides utilities for database operations.
"""

import sqlite3
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Generator
from datetime import datetime

logger = logging.getLogger(__name__)

# Database schema version for future migrations
SCHEMA_VERSION = 1

# Default database path
DEFAULT_DB_PATH = "tickets.db"

# SQL schema definitions
CREATE_CONCERTS_TABLE = """
CREATE TABLE IF NOT EXISTS concerts (
    event_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    venue TEXT,
    event_date DATE,
    threshold_price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_PRICE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    section TEXT,
    ticket_type TEXT,
    availability INTEGER DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES concerts (event_id)
);
"""

CREATE_EMAIL_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    email_type TEXT CHECK (email_type IN ('alert', 'summary')) NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT FALSE
);
"""

# Indexes for better query performance
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_price_history_event_id ON price_history (event_id);",
    "CREATE INDEX IF NOT EXISTS idx_price_history_recorded_at ON price_history (recorded_at);",
    "CREATE INDEX IF NOT EXISTS idx_email_log_event_id ON email_log (event_id);",
    "CREATE INDEX IF NOT EXISTS idx_email_log_sent_at ON email_log (sent_at);"
]

# Schema version table
CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


def get_database_path(config_path: Optional[str] = None) -> str:
    """Get the database file path from configuration or use default."""
    if config_path and os.path.exists(config_path):
        return config_path
    return DEFAULT_DB_PATH


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Create and return a database connection.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        SQLite connection object
        
    Raises:
        DatabaseError: If connection fails
    """
    try:
        if db_path is None:
            db_path = get_database_path()
            
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like row access
        
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        
        logger.debug(f"Connected to database: {db_path}")
        return conn
        
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        raise DatabaseError(f"Database connection failed: {e}")


@contextmanager
def get_db_transaction(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database transactions.
    
    Automatically commits on success or rolls back on exception.
    
    Args:
        db_path: Path to the database file
        
    Yields:
        SQLite connection object
    """
    conn = None
    try:
        conn = get_connection(db_path)
        conn.execute("BEGIN")
        yield conn
        conn.commit()
        logger.debug("Transaction committed successfully")
        
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
        raise
        
    finally:
        if conn:
            conn.close()


def initialize_database(db_path: Optional[str] = None) -> bool:
    """
    Initialize the database with required tables and indexes.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        True if initialization successful, False otherwise
    """
    try:
        with get_db_transaction(db_path) as conn:
            # Create tables
            conn.execute(CREATE_CONCERTS_TABLE)
            conn.execute(CREATE_PRICE_HISTORY_TABLE)
            conn.execute(CREATE_EMAIL_LOG_TABLE)
            conn.execute(CREATE_SCHEMA_VERSION_TABLE)
            
            # Create indexes
            for index_sql in CREATE_INDEXES:
                conn.execute(index_sql)
            
            # Insert or update schema version
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,)
            )
            
            logger.info("Database initialized successfully")
            return True
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def check_database_integrity(db_path: Optional[str] = None) -> bool:
    """
    Check database integrity and schema.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        True if database is healthy, False otherwise
    """
    try:
        with get_connection(db_path) as conn:
            # Check integrity
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                logger.error(f"Database integrity check failed: {result[0]}")
                return False
            
            # Check if all required tables exist
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            
            required_tables = {'concerts', 'price_history', 'email_log', 'schema_version'}
            existing_tables = {row[0] for row in tables}
            
            missing_tables = required_tables - existing_tables
            if missing_tables:
                logger.error(f"Missing required tables: {missing_tables}")
                return False
            
            logger.info("Database integrity check passed")
            return True
            
    except Exception as e:
        logger.error(f"Database integrity check failed: {e}")
        return False


def get_database_stats(db_path: Optional[str] = None) -> dict:
    """
    Get basic database statistics.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        Dictionary with database statistics
    """
    try:
        with get_connection(db_path) as conn:
            stats = {}
            
            # Table row counts
            stats['concerts_count'] = conn.execute(
                "SELECT COUNT(*) FROM concerts"
            ).fetchone()[0]
            
            stats['price_records_count'] = conn.execute(
                "SELECT COUNT(*) FROM price_history"
            ).fetchone()[0]
            
            stats['email_logs_count'] = conn.execute(
                "SELECT COUNT(*) FROM email_log"
            ).fetchone()[0]
            
            # Database file size
            if db_path and os.path.exists(db_path):
                stats['file_size_mb'] = round(os.path.getsize(db_path) / 1024 / 1024, 2)
            else:
                stats['file_size_mb'] = 0
            
            # Schema version
            try:
                version = conn.execute(
                    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
                ).fetchone()
                stats['schema_version'] = version[0] if version else 0
            except sqlite3.OperationalError:
                stats['schema_version'] = 0
            
            return stats
            
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}


def backup_database(db_path: Optional[str] = None, backup_path: Optional[str] = None) -> bool:
    """
    Create a backup of the database.
    
    Args:
        db_path: Path to the source database file
        backup_path: Path for the backup file
        
    Returns:
        True if backup successful, False otherwise
    """
    try:
        if db_path is None:
            db_path = get_database_path()
            
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{db_path}.backup_{timestamp}"
        
        # Ensure backup directory exists
        Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
        
        with get_connection(db_path) as source_conn:
            with sqlite3.connect(backup_path) as backup_conn:
                source_conn.backup(backup_conn)
        
        logger.info(f"Database backed up to: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return False


def reset_database(db_path: Optional[str] = None) -> bool:
    """
    Reset the database by dropping all tables and reinitializing.
    
    WARNING: This will delete all data!
    
    Args:
        db_path: Path to the database file
        
    Returns:
        True if reset successful, False otherwise
    """
    try:
        with get_db_transaction(db_path) as conn:
            # Drop all tables
            conn.execute("DROP TABLE IF EXISTS email_log")
            conn.execute("DROP TABLE IF EXISTS price_history")
            conn.execute("DROP TABLE IF EXISTS concerts")
            conn.execute("DROP TABLE IF EXISTS schema_version")
            
        # Reinitialize
        return initialize_database(db_path)
        
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        return False