"""
Tests for data models in TixScanner.

This module contains tests for Concert, PriceHistory, and EmailLog models
including validation, serialization, and business logic.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal

from src.models import Concert, PriceHistory, EmailLog, EmailType, ValidationError


class TestConcert:
    """Test Concert model."""
    
    def test_concert_creation_valid(self):
        """Test creating a valid concert."""
        concert = Concert(
            event_id="123456789",
            name="Taylor Swift - Eras Tour",
            venue="MetLife Stadium",
            event_date=date(2024, 5, 18),
            threshold_price=Decimal("150.00")
        )
        
        assert concert.event_id == "123456789"
        assert concert.name == "Taylor Swift - Eras Tour"
        assert concert.venue == "MetLife Stadium"
        assert concert.event_date == date(2024, 5, 18)
        assert concert.threshold_price == Decimal("150.00")
        assert isinstance(concert.created_at, datetime)
        assert isinstance(concert.updated_at, datetime)
    
    def test_concert_creation_minimal(self):
        """Test creating concert with minimal required fields."""
        concert = Concert(
            event_id="123",
            name="Test Concert",
            threshold_price=100.0  # Should be converted to Decimal
        )
        
        assert concert.event_id == "123"
        assert concert.name == "Test Concert"
        assert concert.threshold_price == Decimal("100.0")
        assert concert.venue is None
        assert concert.event_date is None
    
    def test_concert_validation_empty_event_id(self):
        """Test validation fails for empty event_id."""
        with pytest.raises(ValidationError, match="Event ID cannot be empty"):
            Concert(
                event_id="",
                name="Test Concert",
                threshold_price=100.0
            )
    
    def test_concert_validation_empty_name(self):
        """Test validation fails for empty name."""
        with pytest.raises(ValidationError, match="Concert name cannot be empty"):
            Concert(
                event_id="123",
                name="",
                threshold_price=100.0
            )
    
    def test_concert_validation_invalid_price(self):
        """Test validation fails for invalid price."""
        with pytest.raises(ValidationError, match="Invalid threshold price format"):
            Concert(
                event_id="123",
                name="Test Concert",
                threshold_price="invalid"
            )
    
    def test_concert_validation_negative_price(self):
        """Test validation fails for negative price."""
        with pytest.raises(ValidationError, match="Threshold price must be positive"):
            Concert(
                event_id="123",
                name="Test Concert",
                threshold_price=-100.0
            )
    
    def test_concert_string_date_parsing(self):
        """Test parsing string date."""
        concert = Concert(
            event_id="123",
            name="Test Concert",
            threshold_price=100.0,
            event_date="2024-05-18"
        )
        
        assert concert.event_date == date(2024, 5, 18)
    
    def test_concert_invalid_date_format(self):
        """Test validation fails for invalid date format."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            Concert(
                event_id="123",
                name="Test Concert",
                threshold_price=100.0,
                event_date="invalid-date"
            )
    
    def test_concert_update_timestamp(self):
        """Test updating timestamp."""
        concert = Concert(
            event_id="123",
            name="Test Concert",
            threshold_price=100.0
        )
        
        original_time = concert.updated_at
        concert.update_timestamp()
        
        assert concert.updated_at > original_time
    
    def test_concert_str_representation(self):
        """Test string representation."""
        concert = Concert(
            event_id="123",
            name="Test Concert",
            venue="Test Venue",
            event_date=date(2024, 5, 18),
            threshold_price=100.0
        )
        
        expected = "Test Concert at Test Venue on 2024-05-18"
        assert str(concert) == expected
    
    def test_concert_equality(self):
        """Test concert equality based on event_id."""
        concert1 = Concert(event_id="123", name="Concert 1", threshold_price=100.0)
        concert2 = Concert(event_id="123", name="Concert 2", threshold_price=200.0)
        concert3 = Concert(event_id="456", name="Concert 1", threshold_price=100.0)
        
        assert concert1 == concert2
        assert concert1 != concert3
    
    def test_concert_hash(self):
        """Test concert hashing for use in sets."""
        concert1 = Concert(event_id="123", name="Concert 1", threshold_price=100.0)
        concert2 = Concert(event_id="123", name="Concert 2", threshold_price=200.0)
        
        concert_set = {concert1, concert2}
        assert len(concert_set) == 1  # Same event_id, so only one in set
    
    def test_concert_to_dict(self):
        """Test converting concert to dictionary."""
        concert = Concert(
            event_id="123",
            name="Test Concert",
            venue="Test Venue",
            event_date=date(2024, 5, 18),
            threshold_price=100.0
        )
        
        data = concert.to_dict()
        
        assert data['event_id'] == "123"
        assert data['name'] == "Test Concert"
        assert data['venue'] == "Test Venue"
        assert data['event_date'] == "2024-05-18"
        assert data['threshold_price'] == 100.0
        assert 'created_at' in data
        assert 'updated_at' in data
    
    def test_concert_from_dict(self):
        """Test creating concert from dictionary."""
        data = {
            'event_id': "123",
            'name': "Test Concert",
            'venue': "Test Venue",
            'event_date': "2024-05-18",
            'threshold_price': 100.0,
            'created_at': "2024-01-01T10:00:00",
            'updated_at': "2024-01-01T11:00:00"
        }
        
        concert = Concert.from_dict(data)
        
        assert concert.event_id == "123"
        assert concert.name == "Test Concert"
        assert concert.venue == "Test Venue"
        assert concert.event_date == date(2024, 5, 18)
        assert concert.threshold_price == Decimal("100.0")


class TestPriceHistory:
    """Test PriceHistory model."""
    
    def test_price_history_creation_valid(self):
        """Test creating valid price history."""
        price = PriceHistory(
            event_id="123",
            price=Decimal("150.00"),
            section="Floor",
            ticket_type="General Admission",
            availability=50
        )
        
        assert price.event_id == "123"
        assert price.price == Decimal("150.00")
        assert price.section == "Floor"
        assert price.ticket_type == "General Admission"
        assert price.availability == 50
        assert isinstance(price.recorded_at, datetime)
    
    def test_price_history_validation_empty_event_id(self):
        """Test validation fails for empty event_id."""
        with pytest.raises(ValidationError, match="Event ID cannot be empty"):
            PriceHistory(
                event_id="",
                price=100.0
            )
    
    def test_price_history_validation_invalid_price(self):
        """Test validation fails for invalid price."""
        with pytest.raises(ValidationError, match="Invalid price format"):
            PriceHistory(
                event_id="123",
                price="invalid"
            )
    
    def test_price_history_validation_negative_price(self):
        """Test validation fails for negative price."""
        with pytest.raises(ValidationError, match="Price must be positive"):
            PriceHistory(
                event_id="123",
                price=-100.0
            )
    
    def test_price_history_validation_negative_availability(self):
        """Test validation fails for negative availability."""
        with pytest.raises(ValidationError, match="Availability cannot be negative"):
            PriceHistory(
                event_id="123",
                price=100.0,
                availability=-1
            )
    
    def test_calculate_change_from_previous(self):
        """Test calculating price change from previous record."""
        previous = PriceHistory(event_id="123", price=Decimal("200.00"))
        current = PriceHistory(event_id="123", price=Decimal("150.00"))
        
        change = current.calculate_change_from(previous)
        
        assert change['amount'] == Decimal("-50.00")
        assert change['percentage'] == Decimal("-25.00")
    
    def test_calculate_change_no_previous(self):
        """Test calculating change with no previous record."""
        current = PriceHistory(event_id="123", price=Decimal("150.00"))
        
        change = current.calculate_change_from(None)
        
        assert change['amount'] == Decimal("0")
        assert change['percentage'] == Decimal("0")
    
    def test_is_significant_drop(self):
        """Test detecting significant price drops."""
        previous = PriceHistory(event_id="123", price=Decimal("200.00"))
        
        # 25% drop (significant)
        current_drop = PriceHistory(event_id="123", price=Decimal("150.00"))
        assert current_drop.is_significant_drop(previous, 10.0) == True
        
        # 5% drop (not significant)
        current_small = PriceHistory(event_id="123", price=Decimal("190.00"))
        assert current_small.is_significant_drop(previous, 10.0) == False
        
        # Price increase
        current_increase = PriceHistory(event_id="123", price=Decimal("220.00"))
        assert current_increase.is_significant_drop(previous, 10.0) == False
    
    def test_price_history_to_dict(self):
        """Test converting price history to dictionary."""
        price = PriceHistory(
            event_id="123",
            price=150.00,
            section="Floor",
            ticket_type="GA",
            availability=25
        )
        
        data = price.to_dict()
        
        assert data['event_id'] == "123"
        assert data['price'] == 150.0
        assert data['section'] == "Floor"
        assert data['ticket_type'] == "GA"
        assert data['availability'] == 25
        assert 'recorded_at' in data
    
    def test_price_history_from_dict(self):
        """Test creating price history from dictionary."""
        data = {
            'id': 1,
            'event_id': "123",
            'price': 150.0,
            'section': "Floor",
            'ticket_type': "GA",
            'availability': 25,
            'recorded_at': "2024-01-01T10:00:00"
        }
        
        price = PriceHistory.from_dict(data)
        
        assert price.id == 1
        assert price.event_id == "123"
        assert price.price == Decimal("150.0")
        assert price.section == "Floor"


class TestEmailLog:
    """Test EmailLog model."""
    
    def test_email_log_creation_valid(self):
        """Test creating valid email log."""
        email_log = EmailLog(
            email_type=EmailType.ALERT,
            recipient="test@example.com",
            event_id="123",
            subject="Price Alert",
            success=True
        )
        
        assert email_log.email_type == EmailType.ALERT
        assert email_log.recipient == "test@example.com"
        assert email_log.event_id == "123"
        assert email_log.subject == "Price Alert"
        assert email_log.success == True
        assert isinstance(email_log.sent_at, datetime)
    
    def test_email_log_string_type_conversion(self):
        """Test converting string email type to enum."""
        email_log = EmailLog(
            email_type="summary",  # String input
            recipient="test@example.com"
        )
        
        assert email_log.email_type == EmailType.SUMMARY
    
    def test_email_log_validation_invalid_type(self):
        """Test validation fails for invalid email type."""
        with pytest.raises(ValidationError, match="Invalid email type"):
            EmailLog(
                email_type="invalid",
                recipient="test@example.com"
            )
    
    def test_email_log_validation_empty_recipient(self):
        """Test validation fails for empty recipient."""
        with pytest.raises(ValidationError, match="Recipient cannot be empty"):
            EmailLog(
                email_type=EmailType.ALERT,
                recipient=""
            )
    
    def test_email_log_validation_invalid_email(self):
        """Test validation fails for invalid email format."""
        with pytest.raises(ValidationError, match="Invalid email format"):
            EmailLog(
                email_type=EmailType.ALERT,
                recipient="invalid-email"
            )
    
    def test_mark_successful(self):
        """Test marking email as successful."""
        email_log = EmailLog(
            email_type=EmailType.ALERT,
            recipient="test@example.com",
            success=False
        )
        
        original_time = email_log.sent_at
        email_log.mark_successful()
        
        assert email_log.success == True
        assert email_log.sent_at >= original_time
    
    def test_mark_failed(self):
        """Test marking email as failed."""
        email_log = EmailLog(
            email_type=EmailType.ALERT,
            recipient="test@example.com",
            success=True
        )
        
        original_time = email_log.sent_at
        email_log.mark_failed()
        
        assert email_log.success == False
        assert email_log.sent_at >= original_time
    
    def test_email_log_str_representation(self):
        """Test string representation."""
        email_log = EmailLog(
            email_type=EmailType.ALERT,
            recipient="test@example.com",
            success=True
        )
        
        str_repr = str(email_log)
        assert "✓" in str_repr
        assert "Alert email" in str_repr
        assert "test@example.com" in str_repr
    
    def test_email_log_to_dict(self):
        """Test converting email log to dictionary."""
        email_log = EmailLog(
            email_type=EmailType.SUMMARY,
            recipient="test@example.com",
            event_id="123",
            subject="Daily Summary",
            success=True
        )
        
        data = email_log.to_dict()
        
        assert data['email_type'] == "summary"
        assert data['recipient'] == "test@example.com"
        assert data['event_id'] == "123"
        assert data['subject'] == "Daily Summary"
        assert data['success'] == True
        assert 'sent_at' in data
    
    def test_email_log_from_dict(self):
        """Test creating email log from dictionary."""
        data = {
            'id': 1,
            'email_type': "alert",
            'recipient': "test@example.com",
            'event_id': "123",
            'subject': "Price Alert",
            'success': True,
            'sent_at': "2024-01-01T10:00:00"
        }
        
        email_log = EmailLog.from_dict(data)
        
        assert email_log.id == 1
        assert email_log.email_type == EmailType.ALERT
        assert email_log.recipient == "test@example.com"
        assert email_log.event_id == "123"


class TestEmailType:
    """Test EmailType enum."""
    
    def test_email_type_values(self):
        """Test enum values."""
        assert EmailType.ALERT.value == "alert"
        assert EmailType.SUMMARY.value == "summary"
    
    def test_email_type_creation(self):
        """Test creating enum from string."""
        alert = EmailType("alert")
        summary = EmailType("summary")
        
        assert alert == EmailType.ALERT
        assert summary == EmailType.SUMMARY