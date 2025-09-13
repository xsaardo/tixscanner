"""
Tests for database operations in TixScanner.

This module contains tests for CRUD operations on concerts,
price history, and email logs.
"""

import pytest
import tempfile
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

from src.database import initialize_database
from src.models import Concert, PriceHistory, EmailLog, EmailType
from src.db_operations import (
    # Concert operations
    add_concert, get_concert, get_all_concerts, update_concert, delete_concert,
    # Price history operations
    add_price_record, get_price_history, get_latest_price, get_price_changes, cleanup_old_prices,
    # Email operations
    log_email, get_recent_emails,
    # Utility operations
    export_data, get_summary_stats
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    
    initialize_database(db_path)
    yield db_path
    
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def sample_concert():
    """Create sample concert for testing."""
    return Concert(
        event_id="123456789",
        name="Taylor Swift - Eras Tour",
        venue="MetLife Stadium",
        event_date=date(2024, 5, 18),
        threshold_price=Decimal("150.00")
    )


class TestConcertOperations:
    """Test concert CRUD operations."""
    
    def test_add_concert_success(self, temp_db, sample_concert):
        """Test successfully adding a concert."""
        assert add_concert(sample_concert, temp_db) == True
        
        # Verify concert was added
        retrieved = get_concert(sample_concert.event_id, temp_db)
        assert retrieved is not None
        assert retrieved.name == sample_concert.name
    
    def test_add_duplicate_concert_fails(self, temp_db, sample_concert):
        """Test adding duplicate concert fails."""
        assert add_concert(sample_concert, temp_db) == True
        assert add_concert(sample_concert, temp_db) == False  # Should fail
    
    def test_get_concert_existing(self, temp_db, sample_concert):
        """Test getting existing concert."""
        add_concert(sample_concert, temp_db)
        
        retrieved = get_concert(sample_concert.event_id, temp_db)
        assert retrieved is not None
        assert retrieved.event_id == sample_concert.event_id
        assert retrieved.name == sample_concert.name
        assert retrieved.venue == sample_concert.venue
        assert retrieved.event_date == sample_concert.event_date
        assert retrieved.threshold_price == sample_concert.threshold_price
    
    def test_get_concert_nonexistent(self, temp_db):
        """Test getting non-existent concert returns None."""
        assert get_concert("nonexistent", temp_db) is None
    
    def test_get_all_concerts_empty(self, temp_db):
        """Test getting all concerts from empty database."""
        concerts = get_all_concerts(temp_db)
        assert concerts == []
    
    def test_get_all_concerts_with_data(self, temp_db):
        """Test getting all concerts with data."""
        concert1 = Concert(event_id="123", name="Concert 1", threshold_price=100.0)
        concert2 = Concert(event_id="456", name="Concert 2", threshold_price=200.0)
        
        add_concert(concert1, temp_db)
        add_concert(concert2, temp_db)
        
        concerts = get_all_concerts(temp_db)
        assert len(concerts) == 2
        
        # Should be ordered by name
        assert concerts[0].name == "Concert 1"
        assert concerts[1].name == "Concert 2"
    
    def test_update_concert_success(self, temp_db, sample_concert):
        """Test successfully updating a concert."""
        add_concert(sample_concert, temp_db)
        
        # Update concert
        sample_concert.name = "Updated Concert Name"
        sample_concert.threshold_price = Decimal("200.00")
        
        assert update_concert(sample_concert, temp_db) == True
        
        # Verify update
        retrieved = get_concert(sample_concert.event_id, temp_db)
        assert retrieved.name == "Updated Concert Name"
        assert retrieved.threshold_price == Decimal("200.00")
    
    def test_update_nonexistent_concert_fails(self, temp_db):
        """Test updating non-existent concert fails."""
        concert = Concert(event_id="nonexistent", name="Test", threshold_price=100.0)
        assert update_concert(concert, temp_db) == False
    
    def test_delete_concert_success(self, temp_db, sample_concert):
        """Test successfully deleting a concert."""
        add_concert(sample_concert, temp_db)
        assert delete_concert(sample_concert.event_id, temp_db) == True
        
        # Verify deletion
        assert get_concert(sample_concert.event_id, temp_db) is None
    
    def test_delete_nonexistent_concert_fails(self, temp_db):
        """Test deleting non-existent concert fails."""
        assert delete_concert("nonexistent", temp_db) == False
    
    def test_delete_concert_removes_price_history(self, temp_db, sample_concert):
        """Test deleting concert also removes its price history."""
        add_concert(sample_concert, temp_db)
        
        # Add price history
        price = PriceHistory(event_id=sample_concert.event_id, price=Decimal("100.00"))
        add_price_record(price, temp_db)
        
        # Delete concert
        assert delete_concert(sample_concert.event_id, temp_db) == True
        
        # Verify price history is also gone
        history = get_price_history(sample_concert.event_id, db_path=temp_db)
        assert history == []


class TestPriceHistoryOperations:
    """Test price history operations."""
    
    def test_add_price_record_success(self, temp_db, sample_concert):
        """Test successfully adding price record."""
        add_concert(sample_concert, temp_db)
        
        price = PriceHistory(
            event_id=sample_concert.event_id,
            price=Decimal("150.00"),
            section="Floor",
            ticket_type="GA",
            availability=50
        )
        
        assert add_price_record(price, temp_db) == True
        assert price.id is not None  # Should be set by database
    
    def test_get_price_history_empty(self, temp_db, sample_concert):
        """Test getting price history for concert with no history."""
        add_concert(sample_concert, temp_db)
        
        history = get_price_history(sample_concert.event_id, db_path=temp_db)
        assert history == []
    
    def test_get_price_history_with_data(self, temp_db, sample_concert):
        """Test getting price history with data."""
        add_concert(sample_concert, temp_db)
        
        # Add multiple price records
        prices = [
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("200.00")),
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("180.00")),
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("160.00"))
        ]
        
        for price in prices:
            add_price_record(price, temp_db)
        
        history = get_price_history(sample_concert.event_id, db_path=temp_db)
        assert len(history) == 3
        
        # Should be ordered by recorded_at
        assert history[0].price == Decimal("200.00")  # First added
        assert history[-1].price == Decimal("160.00")  # Last added
    
    def test_get_price_history_days_filter(self, temp_db, sample_concert):
        """Test getting price history with days filter."""
        add_concert(sample_concert, temp_db)
        
        # Add old price record
        old_price = PriceHistory(
            event_id=sample_concert.event_id,
            price=Decimal("200.00"),
            recorded_at=datetime.now() - timedelta(days=40)
        )
        add_price_record(old_price, temp_db)
        
        # Add recent price record
        recent_price = PriceHistory(
            event_id=sample_concert.event_id,
            price=Decimal("150.00")
        )
        add_price_record(recent_price, temp_db)
        
        # Get last 30 days only
        history = get_price_history(sample_concert.event_id, days=30, db_path=temp_db)
        assert len(history) == 1
        assert history[0].price == Decimal("150.00")
    
    def test_get_latest_price_none(self, temp_db, sample_concert):
        """Test getting latest price when none exists."""
        add_concert(sample_concert, temp_db)
        
        latest = get_latest_price(sample_concert.event_id, temp_db)
        assert latest is None
    
    def test_get_latest_price_with_data(self, temp_db, sample_concert):
        """Test getting latest price with data."""
        add_concert(sample_concert, temp_db)
        
        # Add multiple prices
        prices = [
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("200.00")),
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("180.00")),
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("160.00"))
        ]
        
        for price in prices:
            add_price_record(price, temp_db)
        
        latest = get_latest_price(sample_concert.event_id, temp_db)
        assert latest is not None
        assert latest.price == Decimal("160.00")  # Last added
    
    def test_get_price_changes(self, temp_db, sample_concert):
        """Test getting price changes."""
        add_concert(sample_concert, temp_db)
        
        # Add price history
        prices = [
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("200.00")),
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("150.00")),  # 25% drop
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("160.00"))   # 6.67% increase
        ]
        
        for price in prices:
            add_price_record(price, temp_db)
        
        changes = get_price_changes(sample_concert.event_id, hours=24, db_path=temp_db)
        assert len(changes) == 3
        
        # First record has no change
        assert changes[0][1]['percentage'] == Decimal('0')
        
        # Second record shows 25% drop
        assert changes[1][1]['percentage'] == Decimal('-25.00')
        
        # Third record shows increase
        assert changes[2][1]['percentage'] > 0
    
    def test_cleanup_old_prices(self, temp_db, sample_concert):
        """Test cleaning up old price records."""
        add_concert(sample_concert, temp_db)
        
        # Add old and new prices
        old_price = PriceHistory(
            event_id=sample_concert.event_id,
            price=Decimal("200.00"),
            recorded_at=datetime.now() - timedelta(days=100)
        )
        add_price_record(old_price, temp_db)
        
        recent_price = PriceHistory(
            event_id=sample_concert.event_id,
            price=Decimal("150.00")
        )
        add_price_record(recent_price, temp_db)
        
        # Clean up prices older than 90 days
        deleted_count = cleanup_old_prices(days=90, db_path=temp_db)
        assert deleted_count == 1
        
        # Verify only recent price remains
        history = get_price_history(sample_concert.event_id, days=365, db_path=temp_db)
        assert len(history) == 1
        assert history[0].price == Decimal("150.00")


class TestEmailLogOperations:
    """Test email log operations."""
    
    def test_log_email_success(self, temp_db):
        """Test successfully logging an email."""
        email_log = EmailLog(
            email_type=EmailType.ALERT,
            recipient="test@example.com",
            event_id="123",
            subject="Price Alert",
            success=True
        )
        
        assert log_email(email_log, temp_db) == True
        assert email_log.id is not None  # Should be set by database
    
    def test_get_recent_emails_empty(self, temp_db):
        """Test getting recent emails from empty database."""
        emails = get_recent_emails(temp_db)
        assert emails == []
    
    def test_get_recent_emails_with_data(self, temp_db):
        """Test getting recent emails with data."""
        # Log multiple emails
        emails_to_log = [
            EmailLog(email_type=EmailType.ALERT, recipient="test1@example.com", success=True),
            EmailLog(email_type=EmailType.SUMMARY, recipient="test2@example.com", success=True),
            EmailLog(email_type=EmailType.ALERT, recipient="test3@example.com", success=False)
        ]
        
        for email in emails_to_log:
            log_email(email, temp_db)
        
        recent = get_recent_emails(hours=24, db_path=temp_db)
        assert len(recent) == 3
        
        # Should be ordered by sent_at DESC (most recent first)
        assert recent[0].recipient == "test3@example.com"  # Last logged
    
    def test_get_recent_emails_time_filter(self, temp_db):
        """Test getting recent emails with time filter."""
        # Log old email
        old_email = EmailLog(
            email_type=EmailType.ALERT,
            recipient="old@example.com",
            success=True,
            sent_at=datetime.now() - timedelta(hours=48)
        )
        log_email(old_email, temp_db)
        
        # Log recent email
        recent_email = EmailLog(
            email_type=EmailType.SUMMARY,
            recipient="recent@example.com",
            success=True
        )
        log_email(recent_email, temp_db)
        
        # Get last 24 hours only
        emails = get_recent_emails(hours=24, db_path=temp_db)
        assert len(emails) == 1
        assert emails[0].recipient == "recent@example.com"


class TestUtilityOperations:
    """Test utility operations."""
    
    def test_export_data_empty(self, temp_db):
        """Test exporting data from empty database."""
        data = export_data(temp_db)
        
        assert 'concerts' in data
        assert 'price_history' in data
        assert 'email_logs' in data
        assert 'exported_at' in data
        
        assert data['concerts'] == []
        assert data['price_history'] == []
        assert data['email_logs'] == []
    
    def test_export_data_with_content(self, temp_db, sample_concert):
        """Test exporting data with content."""
        # Add sample data
        add_concert(sample_concert, temp_db)
        
        price = PriceHistory(event_id=sample_concert.event_id, price=Decimal("150.00"))
        add_price_record(price, temp_db)
        
        email_log = EmailLog(email_type=EmailType.ALERT, recipient="test@example.com")
        log_email(email_log, temp_db)
        
        # Export
        data = export_data(temp_db)
        
        assert len(data['concerts']) == 1
        assert len(data['price_history']) == 1
        assert len(data['email_logs']) == 1
        
        # Verify data structure
        assert data['concerts'][0]['event_id'] == sample_concert.event_id
        assert data['price_history'][0]['event_id'] == sample_concert.event_id
        assert data['email_logs'][0]['recipient'] == "test@example.com"
    
    def test_get_summary_stats_empty(self, temp_db):
        """Test getting summary stats from empty database."""
        stats = get_summary_stats(temp_db)
        
        assert stats['total_concerts'] == 0
        assert stats['total_price_records'] == 0
        assert stats['total_emails'] == 0
        assert stats['successful_emails'] == 0
        assert stats['email_success_rate'] == 0
        assert stats['min_price'] == 0
        assert stats['max_price'] == 0
        assert stats['avg_price'] == 0
    
    def test_get_summary_stats_with_data(self, temp_db, sample_concert):
        """Test getting summary stats with data."""
        # Add sample data
        add_concert(sample_concert, temp_db)
        
        # Add price records
        prices = [
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("100.00")),
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("200.00")),
            PriceHistory(event_id=sample_concert.event_id, price=Decimal("150.00"))
        ]
        for price in prices:
            add_price_record(price, temp_db)
        
        # Add email logs
        emails = [
            EmailLog(email_type=EmailType.ALERT, recipient="test1@example.com", success=True),
            EmailLog(email_type=EmailType.SUMMARY, recipient="test2@example.com", success=True),
            EmailLog(email_type=EmailType.ALERT, recipient="test3@example.com", success=False)
        ]
        for email in emails:
            log_email(email, temp_db)
        
        # Get stats
        stats = get_summary_stats(temp_db)
        
        assert stats['total_concerts'] == 1
        assert stats['total_price_records'] == 3
        assert stats['min_price'] == 100.0
        assert stats['max_price'] == 200.0
        assert stats['avg_price'] == 150.0
        assert stats['total_emails'] == 3
        assert stats['successful_emails'] == 2
        assert stats['email_success_rate'] == 66.7