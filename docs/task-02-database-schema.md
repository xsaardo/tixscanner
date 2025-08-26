# Task 2: Database Schema and Models

## Overview
Design and implement the SQLite database schema with Python models for storing concert information, price history, and email logs.

## Acceptance Criteria
- [ ] SQLite database schema is created with all required tables
- [ ] Python database models are implemented with proper typing
- [ ] CRUD operations are working for all entities
- [ ] Database connections are properly managed
- [ ] Data validation and constraints are in place

## Implementation Steps

### 1. Database Schema Design
- [ ] Create `src/database.py` module
- [ ] Define database connection management:
  - [ ] Connection factory function
  - [ ] Context manager for transactions
  - [ ] Error handling for database operations
- [ ] Implement database initialization function
- [ ] Create schema migration system (basic)

### 2. Table Definitions
- [ ] Create `concerts` table:
  ```sql
  CREATE TABLE concerts (
      event_id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      venue TEXT,
      event_date DATE,
      threshold_price DECIMAL(10,2) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- [ ] Create `price_history` table:
  ```sql
  CREATE TABLE price_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      event_id TEXT NOT NULL,
      price DECIMAL(10,2) NOT NULL,
      section TEXT,
      ticket_type TEXT,
      availability INTEGER DEFAULT 0,
      recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (event_id) REFERENCES concerts (event_id)
  );
  ```
- [ ] Create `email_log` table:
  ```sql
  CREATE TABLE email_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      event_id TEXT,
      email_type TEXT CHECK (email_type IN ('alert', 'summary')) NOT NULL,
      recipient TEXT NOT NULL,
      subject TEXT,
      sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      success BOOLEAN DEFAULT FALSE
  );
  ```

### 3. Data Models
- [ ] Create `src/models.py` module
- [ ] Implement Concert model class:
  - [ ] Constructor with type hints
  - [ ] Validation methods
  - [ ] String representation
  - [ ] Comparison methods
- [ ] Implement PriceHistory model class:
  - [ ] Price validation (must be positive)
  - [ ] Date/time handling
  - [ ] Price change calculation methods
- [ ] Implement EmailLog model class:
  - [ ] Email type validation
  - [ ] Success/failure tracking

### 4. Database Operations
- [ ] Create `src/db_operations.py` module
- [ ] Implement Concert operations:
  - [ ] `add_concert(concert: Concert) -> bool`
  - [ ] `get_concert(event_id: str) -> Optional[Concert]`
  - [ ] `get_all_concerts() -> List[Concert]`
  - [ ] `update_concert(concert: Concert) -> bool`
  - [ ] `delete_concert(event_id: str) -> bool`
- [ ] Implement PriceHistory operations:
  - [ ] `add_price_record(price_record: PriceHistory) -> bool`
  - [ ] `get_price_history(event_id: str, days: int = 30) -> List[PriceHistory]`
  - [ ] `get_latest_price(event_id: str) -> Optional[PriceHistory]`
  - [ ] `cleanup_old_prices(days: int = 90) -> int`
- [ ] Implement EmailLog operations:
  - [ ] `log_email(email_log: EmailLog) -> bool`
  - [ ] `get_recent_emails(hours: int = 24) -> List[EmailLog]`

### 5. Database Utilities
- [ ] Create database backup function
- [ ] Implement data export functionality (JSON/CSV)
- [ ] Create database integrity check function
- [ ] Implement database statistics function
- [ ] Add database reset/clean function for testing

### 6. Configuration Integration
- [ ] Read database path from configuration
- [ ] Support for different database locations (dev/prod)
- [ ] Database file permissions and security
- [ ] Connection pooling (if needed)

### 7. Error Handling and Logging
- [ ] Comprehensive exception handling for all database operations
- [ ] Logging for all database interactions
- [ ] Transaction rollback on errors
- [ ] Connection recovery mechanisms

## Testing Criteria
- [ ] Database file is created successfully
- [ ] All tables are created with correct schema
- [ ] CRUD operations work for all models
- [ ] Foreign key constraints are enforced
- [ ] Data validation prevents invalid entries
- [ ] Database connections are properly closed
- [ ] Concurrent access works correctly
- [ ] Database backup/restore functions work

## Files to Create
- `src/database.py` - Database connection and initialization
- `src/models.py` - Data model classes
- `src/db_operations.py` - CRUD operations
- `tests/test_database.py` - Database tests
- `tests/test_models.py` - Model tests

## Dependencies
- Task 1: Project Setup (for basic structure)
- SQLite3 (built-in Python module)

## Estimated Time
4-6 hours

## Notes
- Use type hints throughout for better code documentation
- Implement proper transaction management for data consistency
- Consider adding database versioning for future schema changes
- Keep database operations atomic and handle rollbacks
- Add indexes on frequently queried columns (event_id, recorded_at)

## Sample Usage
```python
# Example usage after implementation
from src.models import Concert
from src.db_operations import add_concert, get_price_history

# Add a concert
concert = Concert(
    event_id="123456789",
    name="Taylor Swift - Eras Tour",
    venue="MetLife Stadium",
    event_date="2024-05-18",
    threshold_price=150.00
)
add_concert(concert)

# Get price history
history = get_price_history("123456789", days=7)
```