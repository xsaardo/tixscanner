"""
Data models for TixScanner application.

This module defines the data model classes for concerts, price history,
and email logs with proper validation and type hints.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EmailType(Enum):
    """Email types for notifications."""
    ALERT = "alert"
    SUMMARY = "summary"


class ValidationError(Exception):
    """Custom exception for model validation errors."""
    pass


@dataclass
class Concert:
    """
    Concert model for tracking ticket prices.
    
    Attributes:
        event_id: Unique identifier from Ticketmaster
        name: Concert/event name
        venue: Venue name
        event_date: Date of the event
        threshold_price: Price threshold for alerts
        created_at: When this record was created
        updated_at: When this record was last updated
    """
    event_id: str
    name: str
    threshold_price: Decimal
    venue: Optional[str] = None
    event_date: Optional[date] = None
    url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validate the concert data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """
        Validate concert data.
        
        Raises:
            ValidationError: If validation fails
        """
        if not self.event_id or not self.event_id.strip():
            raise ValidationError("Event ID cannot be empty")
        
        if not self.name or not self.name.strip():
            raise ValidationError("Concert name cannot be empty")
        
        if not isinstance(self.threshold_price, Decimal):
            try:
                self.threshold_price = Decimal(str(self.threshold_price))
            except (InvalidOperation, TypeError, ValueError):
                raise ValidationError("Invalid threshold price format")
        
        if self.threshold_price <= 0:
            raise ValidationError("Threshold price must be positive")
        
        if self.event_date and isinstance(self.event_date, str):
            try:
                self.event_date = datetime.strptime(self.event_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Invalid date format. Use YYYY-MM-DD")
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()
    
    def __str__(self) -> str:
        """String representation of the concert."""
        venue_str = f" at {self.venue}" if self.venue else ""
        date_str = f" on {self.event_date}" if self.event_date else ""
        return f"{self.name}{venue_str}{date_str}"
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (f"Concert(event_id='{self.event_id}', name='{self.name}', "
                f"threshold_price={self.threshold_price})")
    
    def __eq__(self, other) -> bool:
        """Check equality based on event_id."""
        if not isinstance(other, Concert):
            return False
        return self.event_id == other.event_id
    
    def __hash__(self) -> int:
        """Hash based on event_id for use in sets/dicts."""
        return hash(self.event_id)
    
    def to_dict(self) -> dict:
        """Convert concert to dictionary."""
        return {
            'event_id': self.event_id,
            'name': self.name,
            'venue': self.venue,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'url': self.url,
            'threshold_price': float(self.threshold_price),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Concert':
        """Create Concert instance from dictionary."""
        concert_data = data.copy()
        
        # Convert string dates back to date objects
        if concert_data.get('event_date'):
            concert_data['event_date'] = datetime.fromisoformat(
                concert_data['event_date']
            ).date()
        
        # Convert timestamps
        for field_name in ['created_at', 'updated_at']:
            if concert_data.get(field_name):
                concert_data[field_name] = datetime.fromisoformat(
                    concert_data[field_name]
                )
        
        # Convert price to Decimal
        if 'threshold_price' in concert_data:
            concert_data['threshold_price'] = Decimal(str(concert_data['threshold_price']))
        
        return cls(**concert_data)


@dataclass
class PriceHistory:
    """
    Price history model for tracking ticket price changes.
    
    Attributes:
        event_id: Reference to concert event
        price: Ticket price
        section: Venue section (if available)
        ticket_type: Type of ticket (general, VIP, etc.)
        availability: Number of tickets available
        recorded_at: When this price was recorded
        id: Database primary key (auto-generated)
    """
    event_id: str
    price: Decimal
    section: Optional[str] = None
    ticket_type: Optional[str] = None
    availability: int = 0
    recorded_at: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None
    
    def __post_init__(self) -> None:
        """Validate price history data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """
        Validate price history data.
        
        Raises:
            ValidationError: If validation fails
        """
        if not self.event_id or not self.event_id.strip():
            raise ValidationError("Event ID cannot be empty")
        
        if not isinstance(self.price, Decimal):
            try:
                self.price = Decimal(str(self.price))
            except (InvalidOperation, TypeError, ValueError):
                raise ValidationError("Invalid price format")
        
        if self.price <= 0:
            raise ValidationError("Price must be positive")
        
        if self.availability < 0:
            raise ValidationError("Availability cannot be negative")
    
    def calculate_change_from(self, previous_price: 'PriceHistory') -> dict:
        """
        Calculate price change compared to previous record.
        
        Args:
            previous_price: Previous price record
            
        Returns:
            Dictionary with change amount and percentage
        """
        if not previous_price:
            return {'amount': Decimal('0'), 'percentage': Decimal('0')}
        
        amount_change = self.price - previous_price.price
        percentage_change = (amount_change / previous_price.price) * 100
        
        return {
            'amount': amount_change,
            'percentage': percentage_change.quantize(Decimal('0.01'))
        }
    
    def is_significant_drop(self, previous_price: 'PriceHistory', 
                           threshold_percent: float = 10.0) -> bool:
        """
        Check if price represents a significant drop.
        
        Args:
            previous_price: Previous price record
            threshold_percent: Minimum percentage drop to consider significant
            
        Returns:
            True if price drop is significant
        """
        if not previous_price:
            return False
        
        change = self.calculate_change_from(previous_price)
        return change['percentage'] <= -threshold_percent
    
    def __str__(self) -> str:
        """String representation of price record."""
        section_str = f" ({self.section})" if self.section else ""
        return f"${self.price}{section_str} at {self.recorded_at.strftime('%Y-%m-%d %H:%M')}"
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (f"PriceHistory(event_id='{self.event_id}', price={self.price}, "
                f"recorded_at='{self.recorded_at}')")
    
    def to_dict(self) -> dict:
        """Convert price history to dictionary."""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'price': float(self.price),
            'section': self.section,
            'ticket_type': self.ticket_type,
            'availability': self.availability,
            'recorded_at': self.recorded_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PriceHistory':
        """Create PriceHistory instance from dictionary."""
        price_data = data.copy()
        
        # Convert timestamp
        if price_data.get('recorded_at'):
            price_data['recorded_at'] = datetime.fromisoformat(
                price_data['recorded_at']
            )
        
        # Convert price to Decimal
        if 'price' in price_data:
            price_data['price'] = Decimal(str(price_data['price']))
        
        return cls(**price_data)


@dataclass
class EmailLog:
    """
    Email log model for tracking sent notifications.
    
    Attributes:
        email_type: Type of email (alert or summary)
        recipient: Email recipient
        event_id: Related concert event (optional for summaries)
        subject: Email subject line
        success: Whether email was sent successfully
        sent_at: When email was sent
        id: Database primary key (auto-generated)
    """
    email_type: EmailType
    recipient: str
    event_id: Optional[str] = None
    subject: Optional[str] = None
    success: bool = False
    sent_at: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None
    
    def __post_init__(self) -> None:
        """Validate email log data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """
        Validate email log data.
        
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(self.email_type, EmailType):
            if isinstance(self.email_type, str):
                try:
                    self.email_type = EmailType(self.email_type.lower())
                except ValueError:
                    raise ValidationError(f"Invalid email type: {self.email_type}")
            else:
                raise ValidationError("Email type must be EmailType enum or string")
        
        if not self.recipient or not self.recipient.strip():
            raise ValidationError("Recipient cannot be empty")
        
        # Basic email validation
        if '@' not in self.recipient or '.' not in self.recipient:
            raise ValidationError("Invalid email format")
    
    def mark_successful(self) -> None:
        """Mark the email as successfully sent."""
        self.success = True
        self.sent_at = datetime.now()
    
    def mark_failed(self) -> None:
        """Mark the email as failed to send."""
        self.success = False
        self.sent_at = datetime.now()
    
    def __str__(self) -> str:
        """String representation of email log."""
        status = "✓" if self.success else "✗"
        return (f"{status} {self.email_type.value.title()} email to {self.recipient} "
                f"at {self.sent_at.strftime('%Y-%m-%d %H:%M')}")
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (f"EmailLog(email_type={self.email_type}, recipient='{self.recipient}', "
                f"success={self.success})")
    
    def to_dict(self) -> dict:
        """Convert email log to dictionary."""
        return {
            'id': self.id,
            'email_type': self.email_type.value,
            'recipient': self.recipient,
            'event_id': self.event_id,
            'subject': self.subject,
            'success': self.success,
            'sent_at': self.sent_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EmailLog':
        """Create EmailLog instance from dictionary."""
        email_data = data.copy()
        
        # Convert timestamp
        if email_data.get('sent_at'):
            email_data['sent_at'] = datetime.fromisoformat(
                email_data['sent_at']
            )
        
        # Convert email type
        if 'email_type' in email_data:
            email_data['email_type'] = EmailType(email_data['email_type'])
        
        return cls(**email_data)