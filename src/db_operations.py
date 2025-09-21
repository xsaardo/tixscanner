"""
Database operations for TixScanner application.

This module provides CRUD operations for concerts, price history,
and email logs with proper error handling and logging.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
import json

from .database import get_db_transaction, get_connection, DatabaseError
from .models import Concert, PriceHistory, EmailLog, EmailType, ValidationError

logger = logging.getLogger(__name__)


# Concert Operations
def add_concert(concert: Concert, db_path: Optional[str] = None) -> bool:
    """
    Add a new concert to the database.
    
    Args:
        concert: Concert instance to add
        db_path: Optional database path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        concert.validate()
        
        with get_db_transaction(db_path) as conn:
            conn.execute(
                """
                INSERT INTO concerts 
                (event_id, name, venue, event_date, threshold_price, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    concert.event_id,
                    concert.name,
                    concert.venue,
                    concert.event_date,
                    float(concert.threshold_price),
                    concert.created_at,
                    concert.updated_at
                )
            )
        
        logger.info(f"Added concert: {concert.name} (ID: {concert.event_id})")
        return True
        
    except (ValidationError, sqlite3.IntegrityError) as e:
        logger.error(f"Failed to add concert {concert.event_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error adding concert {concert.event_id}: {e}")
        return False


def get_concert(event_id: str, db_path: Optional[str] = None) -> Optional[Concert]:
    """
    Retrieve a concert by event ID.
    
    Args:
        event_id: Ticketmaster event ID
        db_path: Optional database path
        
    Returns:
        Concert instance if found, None otherwise
    """
    try:
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM concerts WHERE event_id = ?",
                (event_id,)
            ).fetchone()
            
            if row:
                return Concert(
                    event_id=row['event_id'],
                    name=row['name'],
                    venue=row['venue'],
                    event_date=datetime.strptime(row['event_date'], "%Y-%m-%d").date() if row['event_date'] else None,
                    threshold_price=Decimal(str(row['threshold_price'])),
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
            
            return None
            
    except Exception as e:
        logger.error(f"Failed to get concert {event_id}: {e}")
        return None


def ensure_concert_exists(event_id: str, threshold_price: Decimal,
                         db_path: Optional[str] = None) -> Optional[Concert]:
    """
    Ensure a concert exists in the database, creating it if necessary.

    This function will:
    1. Check if the concert exists in the database
    2. If it exists, update the threshold price if different
    3. If it doesn't exist, fetch details from API and create it

    Args:
        event_id: Ticketmaster event ID
        threshold_price: Price threshold for alerts
        db_path: Optional database path

    Returns:
        Concert instance if successful, None if failed
    """
    try:
        # Check if concert already exists
        existing_concert = get_concert(event_id, db_path)

        if existing_concert:
            # Update threshold price if different
            if existing_concert.threshold_price != threshold_price:
                logger.info(f"Updating threshold for {event_id}: ${existing_concert.threshold_price} → ${threshold_price}")
                update_concert_threshold(event_id, threshold_price, db_path)
                existing_concert.threshold_price = threshold_price

            return existing_concert

        # Concert doesn't exist, need to fetch details and create it
        logger.info(f"Concert {event_id} not in database, fetching details from API...")

        # We'll need to import this here to avoid circular imports
        from .ticketmaster_api import TicketmasterAPI
        from .config_manager import ConfigManager

        # Get API key from config
        config = ConfigManager()
        api_key = config.get_ticketmaster_api_key()
        api = TicketmasterAPI(api_key)

        # Fetch event details
        event_details = api.get_event_details(event_id)

        if not event_details:
            logger.error(f"Could not fetch details for event {event_id}")
            return None

        # Create concert from API data
        concert = Concert(
            event_id=event_id,
            name=event_details.get('name', f'Event {event_id}'),
            venue=event_details.get('venue', 'Unknown Venue'),
            event_date=datetime.strptime(event_details['date'], "%Y-%m-%d").date() if event_details.get('date') else None,
            threshold_price=threshold_price
        )

        # Add to database
        if add_concert(concert, db_path):
            logger.info(f"Created new concert record: {concert.name}")
            return concert
        else:
            logger.error(f"Failed to add concert {event_id} to database")
            return None

    except Exception as e:
        logger.error(f"Error ensuring concert {event_id} exists: {e}")
        return None


def update_concert_threshold(event_id: str, threshold_price: Decimal,
                           db_path: Optional[str] = None) -> bool:
    """
    Update the threshold price for a concert.

    Args:
        event_id: Ticketmaster event ID
        threshold_price: New threshold price
        db_path: Optional database path

    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_transaction(db_path) as conn:
            cursor = conn.execute(
                "UPDATE concerts SET threshold_price = ?, updated_at = ? WHERE event_id = ?",
                (float(threshold_price), datetime.now().isoformat(), event_id)
            )

            if cursor.rowcount == 0:
                logger.warning(f"No concert found with event_id: {event_id}")
                return False

            logger.debug(f"Updated threshold for {event_id}: ${threshold_price}")
            return True

    except Exception as e:
        logger.error(f"Failed to update threshold for {event_id}: {e}")
        return False


def get_all_concerts(db_path: Optional[str] = None) -> List[Concert]:
    """
    Retrieve all concerts from the database.
    
    Args:
        db_path: Optional database path
        
    Returns:
        List of Concert instances
    """
    try:
        concerts = []
        
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM concerts ORDER BY name"
            ).fetchall()
            
            for row in rows:
                concert = Concert(
                    event_id=row['event_id'],
                    name=row['name'],
                    venue=row['venue'],
                    event_date=datetime.strptime(row['event_date'], "%Y-%m-%d").date() if row['event_date'] else None,
                    threshold_price=Decimal(str(row['threshold_price'])),
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
                concerts.append(concert)
        
        logger.debug(f"Retrieved {len(concerts)} concerts")
        return concerts
        
    except Exception as e:
        logger.error(f"Failed to get all concerts: {e}")
        return []


def update_concert(concert: Concert, db_path: Optional[str] = None) -> bool:
    """
    Update an existing concert.
    
    Args:
        concert: Concert instance with updated data
        db_path: Optional database path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        concert.validate()
        concert.update_timestamp()
        
        with get_db_transaction(db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE concerts 
                SET name = ?, venue = ?, event_date = ?, threshold_price = ?, updated_at = ?
                WHERE event_id = ?
                """,
                (
                    concert.name,
                    concert.venue,
                    concert.event_date,
                    float(concert.threshold_price),
                    concert.updated_at,
                    concert.event_id
                )
            )
            
            if cursor.rowcount == 0:
                logger.warning(f"No concert found with event_id: {concert.event_id}")
                return False
        
        logger.info(f"Updated concert: {concert.name} (ID: {concert.event_id})")
        return True
        
    except (ValidationError, sqlite3.Error) as e:
        logger.error(f"Failed to update concert {concert.event_id}: {e}")
        return False


def delete_concert(event_id: str, db_path: Optional[str] = None) -> bool:
    """
    Delete a concert and all its price history.
    
    Args:
        event_id: Ticketmaster event ID
        db_path: Optional database path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_transaction(db_path) as conn:
            # Delete price history first (foreign key constraint)
            conn.execute("DELETE FROM price_history WHERE event_id = ?", (event_id,))
            
            # Delete concert
            cursor = conn.execute("DELETE FROM concerts WHERE event_id = ?", (event_id,))
            
            if cursor.rowcount == 0:
                logger.warning(f"No concert found with event_id: {event_id}")
                return False
        
        logger.info(f"Deleted concert with event_id: {event_id}")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Failed to delete concert {event_id}: {e}")
        return False


# Price History Operations
def add_price_record(price_record: PriceHistory, db_path: Optional[str] = None) -> bool:
    """
    Add a price history record.
    
    Args:
        price_record: PriceHistory instance to add
        db_path: Optional database path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        price_record.validate()
        
        with get_db_transaction(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO price_history 
                (event_id, price, section, ticket_type, availability, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    price_record.event_id,
                    float(price_record.price),
                    price_record.section,
                    price_record.ticket_type,
                    price_record.availability,
                    price_record.recorded_at
                )
            )
            
            price_record.id = cursor.lastrowid
        
        logger.debug(f"Added price record for {price_record.event_id}: ${price_record.price}")
        return True
        
    except (ValidationError, sqlite3.Error) as e:
        logger.error(f"Failed to add price record: {e}")
        return False


def get_price_history(event_id: str, days: int = 30, db_path: Optional[str] = None) -> List[PriceHistory]:
    """
    Retrieve price history for an event.
    
    Args:
        event_id: Ticketmaster event ID
        days: Number of days of history to retrieve
        db_path: Optional database path
        
    Returns:
        List of PriceHistory instances ordered by recorded_at
    """
    try:
        since_date = datetime.now() - timedelta(days=int(days))
        price_history = []
        
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM price_history 
                WHERE event_id = ? AND recorded_at >= ?
                ORDER BY recorded_at
                """,
                (event_id, since_date.isoformat())
            ).fetchall()
            
            for row in rows:
                record = PriceHistory(
                    id=row['id'],
                    event_id=row['event_id'],
                    price=Decimal(str(row['price'])),
                    section=row['section'],
                    ticket_type=row['ticket_type'],
                    availability=row['availability'],
                    recorded_at=datetime.fromisoformat(row['recorded_at'])
                )
                price_history.append(record)
        
        logger.debug(f"Retrieved {len(price_history)} price records for {event_id}")
        return price_history
        
    except Exception as e:
        logger.error(f"Failed to get price history for {event_id}: {e}")
        return []


def get_latest_section_price(event_id: str, section: str, db_path: Optional[str] = None) -> Optional[PriceHistory]:
    """
    Get the most recent price for a specific section of an event.

    Args:
        event_id: Ticketmaster event ID
        section: Section name
        db_path: Optional database path

    Returns:
        Most recent PriceHistory for the section or None
    """
    try:
        with get_connection(db_path) as conn:
            row = conn.execute(
                """
                SELECT * FROM price_history
                WHERE event_id = ? AND section = ?
                ORDER BY recorded_at DESC
                LIMIT 1
                """,
                (event_id, section)
            ).fetchone()

            if row:
                return PriceHistory(
                    id=row['id'],
                    event_id=row['event_id'],
                    price=Decimal(str(row['price'])),
                    section=row['section'],
                    ticket_type=row['ticket_type'],
                    availability=row['availability'],
                    recorded_at=datetime.fromisoformat(row['recorded_at'])
                )

            return None

    except Exception as e:
        logger.error(f"Failed to get latest section price for {event_id}/{section}: {e}")
        return None


def get_latest_price(event_id: str, db_path: Optional[str] = None) -> Optional[PriceHistory]:
    """
    Get the most recent price for an event.
    
    Args:
        event_id: Ticketmaster event ID
        db_path: Optional database path
        
    Returns:
        Most recent PriceHistory instance or None
    """
    try:
        with get_connection(db_path) as conn:
            row = conn.execute(
                """
                SELECT * FROM price_history 
                WHERE event_id = ?
                ORDER BY recorded_at DESC
                LIMIT 1
                """,
                (event_id,)
            ).fetchone()
            
            if row:
                return PriceHistory(
                    id=row['id'],
                    event_id=row['event_id'],
                    price=Decimal(str(row['price'])),
                    section=row['section'],
                    ticket_type=row['ticket_type'],
                    availability=row['availability'],
                    recorded_at=datetime.fromisoformat(row['recorded_at'])
                )
            
            return None
            
    except Exception as e:
        logger.error(f"Failed to get latest price for {event_id}: {e}")
        return None


def get_price_changes(event_id: str, hours: int = 24, db_path: Optional[str] = None) -> List[Tuple[PriceHistory, dict]]:
    """
    Get price changes for an event within specified hours.
    
    Args:
        event_id: Ticketmaster event ID
        hours: Number of hours to look back
        db_path: Optional database path
        
    Returns:
        List of tuples (PriceHistory, change_info)
    """
    try:
        since_time = datetime.now() - timedelta(hours=hours)
        
        history = get_price_history(event_id, days=max(1, hours // 24 + 1), db_path=db_path)
        recent_history = [p for p in history if p.recorded_at >= since_time]
        
        changes = []
        for i, current_price in enumerate(recent_history):
            if i == 0:
                # First record, no previous to compare
                change_info = {'amount': Decimal('0'), 'percentage': Decimal('0')}
            else:
                previous_price = recent_history[i - 1]
                change_info = current_price.calculate_change_from(previous_price)
            
            changes.append((current_price, change_info))
        
        return changes
        
    except Exception as e:
        logger.error(f"Failed to get price changes for {event_id}: {e}")
        return []


def cleanup_old_prices(days: int = 90, db_path: Optional[str] = None) -> int:
    """
    Remove old price history records.
    
    Args:
        days: Number of days to keep (delete older records)
        db_path: Optional database path
        
    Returns:
        Number of records deleted
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with get_db_transaction(db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM price_history WHERE recorded_at < ?",
                (cutoff_date,)
            )
            
            deleted_count = cursor.rowcount
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old price records (older than {days} days)")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup old prices: {e}")
        return 0


# Email Log Operations
def log_email(email_log: EmailLog, db_path: Optional[str] = None) -> bool:
    """
    Log an email notification.
    
    Args:
        email_log: EmailLog instance to add
        db_path: Optional database path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        email_log.validate()
        
        with get_db_transaction(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO email_log 
                (event_id, email_type, recipient, subject, success, sent_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    email_log.event_id,
                    email_log.email_type.value,
                    email_log.recipient,
                    email_log.subject,
                    email_log.success,
                    email_log.sent_at
                )
            )
            
            email_log.id = cursor.lastrowid
        
        logger.debug(f"Logged email: {email_log.email_type.value} to {email_log.recipient}")
        return True
        
    except (ValidationError, sqlite3.Error) as e:
        logger.error(f"Failed to log email: {e}")
        return False


def get_recent_emails(hours: int = 24, db_path: Optional[str] = None) -> List[EmailLog]:
    """
    Retrieve recent email logs.
    
    Args:
        hours: Number of hours to look back
        db_path: Optional database path
        
    Returns:
        List of EmailLog instances
    """
    try:
        since_time = datetime.now() - timedelta(hours=hours)
        email_logs = []
        
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM email_log 
                WHERE sent_at >= ?
                ORDER BY sent_at DESC
                """,
                (since_time,)
            ).fetchall()
            
            for row in rows:
                email_log = EmailLog(
                    id=row['id'],
                    event_id=row['event_id'],
                    email_type=EmailType(row['email_type']),
                    recipient=row['recipient'],
                    subject=row['subject'],
                    success=bool(row['success']),
                    sent_at=datetime.fromisoformat(row['sent_at'])
                )
                email_logs.append(email_log)
        
        logger.debug(f"Retrieved {len(email_logs)} email logs from last {hours} hours")
        return email_logs
        
    except Exception as e:
        logger.error(f"Failed to get recent emails: {e}")
        return []


# Data Export Operations
def export_data(db_path: Optional[str] = None) -> dict:
    """
    Export all data to a dictionary for backup/analysis.
    
    Args:
        db_path: Optional database path
        
    Returns:
        Dictionary containing all data
    """
    try:
        concerts = get_all_concerts(db_path)
        all_data = {
            'concerts': [c.to_dict() for c in concerts],
            'price_history': [],
            'email_logs': get_recent_emails(hours=24*30, db_path=db_path)  # 30 days
        }
        
        # Get price history for all concerts
        for concert in concerts:
            history = get_price_history(concert.event_id, days=90, db_path=db_path)
            all_data['price_history'].extend([h.to_dict() for h in history])
        
        all_data['email_logs'] = [e.to_dict() for e in all_data['email_logs']]
        
        all_data['exported_at'] = datetime.now().isoformat()
        
        logger.info("Data export completed successfully")
        return all_data
        
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        return {}


def get_summary_stats(db_path: Optional[str] = None) -> dict:
    """
    Get summary statistics for the application.
    
    Args:
        db_path: Optional database path
        
    Returns:
        Dictionary with summary statistics
    """
    try:
        stats = {}
        
        with get_connection(db_path) as conn:
            # Concert stats
            stats['total_concerts'] = conn.execute("SELECT COUNT(*) FROM concerts").fetchone()[0]
            
            # Price stats
            stats['total_price_records'] = conn.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]
            
            price_stats = conn.execute(
                """
                SELECT 
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    AVG(price) as avg_price
                FROM price_history
                """
            ).fetchone()
            
            stats['min_price'] = float(price_stats['min_price']) if price_stats['min_price'] else 0
            stats['max_price'] = float(price_stats['max_price']) if price_stats['max_price'] else 0
            stats['avg_price'] = round(float(price_stats['avg_price']), 2) if price_stats['avg_price'] else 0
            
            # Email stats
            email_stats = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_emails,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_emails
                FROM email_log
                """
            ).fetchone()
            
            stats['total_emails'] = email_stats['total_emails']
            stats['successful_emails'] = email_stats['successful_emails'] or 0
            stats['email_success_rate'] = (
                round(stats['successful_emails'] / stats['total_emails'] * 100, 1)
                if stats['total_emails'] > 0 else 0
            )
        
        logger.debug("Generated summary statistics")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get summary stats: {e}")
        return {}