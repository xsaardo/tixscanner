"""
Tests for database operations in TixScanner.

This module contains tests for database connections, schema creation,
and database utilities.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, date
from decimal import Decimal

from src.database import (
    get_connection, get_db_transaction, initialize_database,
    check_database_integrity, get_database_stats, backup_database,
    reset_database, DatabaseError
)


class TestDatabaseConnection:
    """Test database connection management."""
    
    def test_get_connection_creates_file(self):
        """Test that get_connection creates database file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            conn = get_connection(db_path)
            assert os.path.exists(db_path)
            conn.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_connection_has_row_factory(self):
        """Test that connections have dict-like row access."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            conn = get_connection(db_path)
            assert conn.row_factory == sqlite3.Row
            conn.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_foreign_keys_enabled(self):
        """Test that foreign key constraints are enabled."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            conn = get_connection(db_path)
            result = conn.execute("PRAGMA foreign_keys").fetchone()
            assert result[0] == 1  # Foreign keys enabled
            conn.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestDatabaseTransaction:
    """Test database transaction management."""
    
    def test_transaction_commits_on_success(self):
        """Test that transaction commits when no exception occurs."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            initialize_database(db_path)
            
            with get_db_transaction(db_path) as conn:
                conn.execute(
                    "INSERT INTO concerts (event_id, name, threshold_price) VALUES (?, ?, ?)",
                    ("test123", "Test Concert", 100.0)
                )
            
            # Verify data was committed
            with get_connection(db_path) as conn:
                result = conn.execute(
                    "SELECT COUNT(*) FROM concerts WHERE event_id = ?",
                    ("test123",)
                ).fetchone()
                assert result[0] == 1
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_transaction_rolls_back_on_exception(self):
        """Test that transaction rolls back when exception occurs."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            initialize_database(db_path)
            
            with pytest.raises(sqlite3.IntegrityError):
                with get_db_transaction(db_path) as conn:
                    conn.execute(
                        "INSERT INTO concerts (event_id, name, threshold_price) VALUES (?, ?, ?)",
                        ("test123", "Test Concert", 100.0)
                    )
                    # Try to insert duplicate primary key
                    conn.execute(
                        "INSERT INTO concerts (event_id, name, threshold_price) VALUES (?, ?, ?)",
                        ("test123", "Another Concert", 200.0)
                    )
            
            # Verify no data was committed
            with get_connection(db_path) as conn:
                result = conn.execute("SELECT COUNT(*) FROM concerts").fetchone()
                assert result[0] == 0
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestDatabaseInitialization:
    """Test database schema initialization."""
    
    def test_initialize_creates_all_tables(self):
        """Test that initialize_database creates all required tables."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            assert initialize_database(db_path) == True
            
            with get_connection(db_path) as conn:
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                
                table_names = {row[0] for row in tables}
                required_tables = {'concerts', 'price_history', 'email_log', 'schema_version'}
                
                assert required_tables.issubset(table_names)
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_initialize_creates_indexes(self):
        """Test that initialize_database creates indexes."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            assert initialize_database(db_path) == True
            
            with get_connection(db_path) as conn:
                indexes = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
                
                index_names = {row[0] for row in indexes if row[0]}  # Filter out None values
                expected_indexes = {
                    'idx_price_history_event_id',
                    'idx_price_history_recorded_at',
                    'idx_email_log_event_id',
                    'idx_email_log_sent_at'
                }
                
                assert expected_indexes.issubset(index_names)
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_initialize_sets_schema_version(self):
        """Test that initialize_database sets schema version."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            assert initialize_database(db_path) == True
            
            with get_connection(db_path) as conn:
                version = conn.execute(
                    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
                ).fetchone()
                
                assert version[0] == 1  # Current schema version
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestDatabaseIntegrity:
    """Test database integrity checking."""
    
    def test_integrity_check_passes_on_healthy_db(self):
        """Test integrity check on healthy database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            initialize_database(db_path)
            assert check_database_integrity(db_path) == True
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_integrity_check_fails_on_missing_tables(self):
        """Test integrity check fails when tables are missing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            # Create database but don't initialize properly
            conn = get_connection(db_path)
            conn.execute("CREATE TABLE dummy (id INTEGER)")
            conn.close()
            
            assert check_database_integrity(db_path) == False
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestDatabaseStats:
    """Test database statistics."""
    
    def test_stats_on_empty_database(self):
        """Test statistics on empty database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            initialize_database(db_path)
            stats = get_database_stats(db_path)
            
            assert stats['concerts_count'] == 0
            assert stats['price_records_count'] == 0
            assert stats['email_logs_count'] == 0
            assert stats['schema_version'] == 1
            assert 'file_size_mb' in stats
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_stats_with_data(self):
        """Test statistics with sample data."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            initialize_database(db_path)
            
            with get_db_transaction(db_path) as conn:
                # Add sample data
                conn.execute(
                    "INSERT INTO concerts (event_id, name, threshold_price) VALUES (?, ?, ?)",
                    ("test123", "Test Concert", 100.0)
                )
                conn.execute(
                    "INSERT INTO price_history (event_id, price) VALUES (?, ?)",
                    ("test123", 150.0)
                )
            
            stats = get_database_stats(db_path)
            
            assert stats['concerts_count'] == 1
            assert stats['price_records_count'] == 1
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestDatabaseBackup:
    """Test database backup functionality."""
    
    def test_backup_creates_copy(self):
        """Test that backup creates a copy of the database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.backup') as backup_tmp:
            backup_path = backup_tmp.name
        
        try:
            initialize_database(db_path)
            
            # Add some data
            with get_db_transaction(db_path) as conn:
                conn.execute(
                    "INSERT INTO concerts (event_id, name, threshold_price) VALUES (?, ?, ?)",
                    ("test123", "Test Concert", 100.0)
                )
            
            assert backup_database(db_path, backup_path) == True
            assert os.path.exists(backup_path)
            
            # Verify backup contains the data
            with get_connection(backup_path) as conn:
                result = conn.execute("SELECT COUNT(*) FROM concerts").fetchone()
                assert result[0] == 1
        finally:
            for path in [db_path, backup_path]:
                if os.path.exists(path):
                    os.unlink(path)


class TestDatabaseReset:
    """Test database reset functionality."""
    
    def test_reset_clears_and_reinitializes(self):
        """Test that reset clears database and reinitializes."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        try:
            initialize_database(db_path)
            
            # Add some data
            with get_db_transaction(db_path) as conn:
                conn.execute(
                    "INSERT INTO concerts (event_id, name, threshold_price) VALUES (?, ?, ?)",
                    ("test123", "Test Concert", 100.0)
                )
            
            # Verify data exists
            with get_connection(db_path) as conn:
                result = conn.execute("SELECT COUNT(*) FROM concerts").fetchone()
                assert result[0] == 1
            
            # Reset database
            assert reset_database(db_path) == True
            
            # Verify data is gone and structure is intact
            with get_connection(db_path) as conn:
                result = conn.execute("SELECT COUNT(*) FROM concerts").fetchone()
                assert result[0] == 0
                
                # Verify tables still exist
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                table_names = {row[0] for row in tables}
                required_tables = {'concerts', 'price_history', 'email_log', 'schema_version'}
                assert required_tables.issubset(table_names)
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)