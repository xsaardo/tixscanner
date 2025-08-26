# Task 5: Price Monitoring and Alerts

## Overview
Implement the core price monitoring system that checks ticket prices, detects price drops, triggers alerts, and coordinates the overall monitoring workflow.

## Acceptance Criteria
- [ ] Price monitoring system runs continuously
- [ ] Price changes are detected accurately
- [ ] Threshold-based alerts are triggered correctly
- [ ] Price data is stored with complete history
- [ ] Monitoring frequency is configurable
- [ ] System handles errors gracefully and continues monitoring

## Implementation Steps

### 1. Core Monitoring Engine
- [ ] Create `src/price_monitor.py` module
- [ ] Implement main monitoring class:
  - [ ] `PriceMonitor` class with configuration management
  - [ ] Price checking workflow orchestration
  - [ ] Error handling and recovery mechanisms
  - [ ] Monitoring state management
- [ ] Configuration integration:
  - [ ] Load monitoring settings from config.ini
  - [ ] Support for different check frequencies
  - [ ] Threshold management per concert
  - [ ] Enable/disable monitoring per concert

### 2. Price Checking Logic
- [ ] Implement price checking workflow:
  - [ ] `check_all_concerts()` - Main monitoring loop
  - [ ] `check_concert_prices(event_id: str)` - Individual concert check
  - [ ] Integration with Ticketmaster API client
  - [ ] Price data validation and cleaning
- [ ] Price comparison logic:
  - [ ] Compare current prices with historical data
  - [ ] Calculate percentage changes
  - [ ] Identify significant price drops
  - [ ] Track different ticket sections/types

### 3. Alert Trigger System
- [ ] Implement alert triggering logic:
  - [ ] `evaluate_price_alerts(event_id: str, new_prices: List)` 
  - [ ] Threshold comparison for each ticket type
  - [ ] Cooldown period to prevent spam alerts
  - [ ] Alert priority and urgency calculation
- [ ] Alert conditions:
  - [ ] Price drops below user-defined threshold
  - [ ] Significant percentage drops (configurable)
  - [ ] New ticket availability alerts
  - [ ] Price trend change alerts (optional)

### 4. Data Processing and Storage
- [ ] Implement price data processing:
  - [ ] Clean and validate price data from API
  - [ ] Handle missing or invalid price information
  - [ ] Normalize price formats and currencies
  - [ ] Store price history with metadata
- [ ] Database integration:
  - [ ] Save all price checks to database
  - [ ] Update concert information if changed
  - [ ] Log monitoring activities
  - [ ] Maintain price history retention policy

### 5. Notification Coordination
- [ ] Implement notification workflow:
  - [ ] Coordinate with email system for alerts
  - [ ] Queue notifications for batch processing
  - [ ] Handle notification failures gracefully
  - [ ] Track notification delivery status
- [ ] Alert deduplication:
  - [ ] Prevent duplicate alerts for same price drop
  - [ ] Time-based alert throttling
  - [ ] Smart alert grouping for multiple sections

### 6. Monitoring Statistics and Health
- [ ] Implement monitoring metrics:
  - [ ] Track successful vs failed price checks
  - [ ] Monitor API response times
  - [ ] Calculate alert trigger rates
  - [ ] Database query performance metrics
- [ ] Health monitoring:
  - [ ] System uptime tracking
  - [ ] Error rate monitoring
  - [ ] Memory and performance monitoring
  - [ ] Alert for system failures

### 7. Configuration Management
- [ ] Dynamic configuration support:
  - [ ] Reload configuration without restart
  - [ ] Per-concert monitoring settings
  - [ ] Global monitoring preferences
  - [ ] Debug and logging level configuration
- [ ] Concert management integration:
  - [ ] Read tracked concerts from config.ini
  - [ ] Support adding/removing concerts dynamically
  - [ ] Validate concert configurations
  - [ ] Handle configuration errors gracefully

### 8. Error Handling and Recovery
- [ ] Comprehensive error handling:
  - [ ] API failures and timeouts
  - [ ] Database connection issues
  - [ ] Email delivery failures
  - [ ] Configuration file errors
- [ ] Recovery mechanisms:
  - [ ] Automatic retry with exponential backoff
  - [ ] Graceful degradation for partial failures
  - [ ] Continue monitoring other concerts if one fails
  - [ ] System restart on critical failures

## Testing Criteria
- [ ] Price monitoring detects actual price changes
- [ ] Alerts are triggered when prices drop below thresholds
- [ ] System continues monitoring after individual failures
- [ ] Configuration changes are applied correctly
- [ ] Price history is stored accurately
- [ ] Monitoring frequency matches configuration
- [ ] System handles API rate limits properly
- [ ] Memory usage remains stable over time

## Files to Create
- `src/price_monitor.py` - Main monitoring engine
- `src/alert_manager.py` - Alert triggering logic
- `src/monitoring_config.py` - Configuration management
- `tests/test_price_monitor.py` - Monitoring system tests
- `tests/test_alert_manager.py` - Alert logic tests

## Dependencies
- Task 2: Database Schema (for price storage)
- Task 3: Ticketmaster API Integration (for price fetching)
- Task 4: Email System (for notifications)
- `schedule` library for timing

## Estimated Time
4-6 hours

## Notes
- Implement robust error handling to ensure continuous monitoring
- Use appropriate data structures for efficient price comparison
- Consider implementing circuit breakers for external dependencies
- Log detailed information for debugging price detection issues
- Optimize database queries for large price history datasets

## Configuration Examples

### config.ini monitoring section
```ini
[monitoring]
check_frequency_hours = 2
minimum_price_drop_percent = 10
alert_cooldown_hours = 6
max_retries = 3
enable_trend_alerts = false
```

### Per-concert thresholds
```ini
[concerts]
# Format: event_id = threshold_price
1234567890 = 150.00
0987654321 = 75.00
```

## Monitoring Workflow
```python
# High-level monitoring workflow
1. Load configuration and tracked concerts
2. For each concert:
   a. Fetch current prices from Ticketmaster API
   b. Compare with previous prices and thresholds
   c. Store price data in database
   d. Trigger alerts if conditions are met
   e. Log monitoring activity
3. Handle any errors and continue with next concert
4. Wait for next monitoring cycle
```

## Sample Usage
```python
# Example usage after implementation
from src.price_monitor import PriceMonitor

# Initialize and start monitoring
monitor = PriceMonitor()
monitor.start_monitoring()  # Runs continuously

# Manual price check
results = monitor.check_all_concerts()
print(f"Checked {len(results)} concerts")

# Check specific concert
price_changes = monitor.check_concert_prices("123456789")
if price_changes:
    print("Price changes detected!")
```

## Alert Logic Example
```python
def should_trigger_alert(current_price: float, threshold: float, 
                        last_alert_time: datetime) -> bool:
    # Check if price is below threshold
    if current_price > threshold:
        return False
    
    # Check cooldown period (prevent spam)
    if last_alert_time and (datetime.now() - last_alert_time).hours < 6:
        return False
    
    return True
```