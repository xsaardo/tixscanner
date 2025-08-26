# TixScanner - Ticket Price Tracking Specification

## Overview
Single-user Python application that tracks concert ticket prices via Ticketmaster API and sends email notifications when prices drop below specified thresholds.

## Core Features
- Track specific concert ticket prices from Ticketmaster API
- Email alerts when resale prices drop below user-defined thresholds
- Daily email summaries with price graphs and purchase links
- Local SQLite database for price history storage
- Configuration-based concert management

## Architecture

### Simple Monolithic Design
```
┌─────────────────────────────────────┐
│        ticket_tracker.py           │
│  ┌─────────────────────────────┐    │
│  │     Price Checker          │    │
│  │   (scheduled function)      │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │   Email Notifications      │    │
│  │    with Price Graphs       │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │    Local SQLite DB         │    │
│  │  (tracked concerts & prices)│    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

## Tech Stack

### Language & Framework
- **Python 3.8+** - Primary language
- **SQLite** - Local database (built-in)
- **Gmail SMTP** - Email delivery (free)

### Core Libraries
```python
# API & Web requests
requests          # Ticketmaster API calls
beautifulsoup4    # Backup web scraping if needed

# Database
sqlite3           # Built-in, no installation needed

# Email
smtplib          # Built-in Gmail SMTP
email.mime       # Built-in email formatting

# Scheduling & Configuration
schedule         # Simple job scheduling
python-dotenv    # Environment variables
configparser     # Configuration management

# Data visualization
matplotlib       # Price charts
pandas           # Price history analysis

# Utilities
datetime         # Built-in date/time handling
```

## Project Structure
```
ticket_tracker/
├── main.py              # Main application
├── config.ini           # Concert tracking configuration
├── .env                 # API keys & email credentials
├── tickets.db           # SQLite database
├── requirements.txt     # Python dependencies
└── docs/
    └── specs.md         # This specification
```

## Configuration Management

### config.ini Format
```ini
[api]
ticketmaster_key = your_api_key_here

[email]
gmail_user = your.email@gmail.com
gmail_password = your_app_password_here
recipient = your.email@gmail.com

[monitoring]
check_frequency_hours = 2
daily_summary_time = 09:00
minimum_price_drop_percent = 10

[concerts]
# Format: event_id = max_price_threshold
1234567890 = 150.00
0987654321 = 75.00
1122334455 = 200.00
```

### Environment Variables (.env)
```
TICKETMASTER_API_KEY=your_key_here
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
```

## Database Schema

### SQLite Tables
```sql
-- Tracked concerts
CREATE TABLE concerts (
    event_id TEXT PRIMARY KEY,
    name TEXT,
    venue TEXT,
    date DATE,
    threshold_price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Price history
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    price DECIMAL(10,2),
    section TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES concerts (event_id)
);

-- Email log
CREATE TABLE email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    email_type TEXT, -- 'alert' or 'summary'
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Email System

### Alert Email Format
```
🚨 Price Drop Alert!

Taylor Swift - MetLife Stadium
New Price: $140 (↓ 15% from $165)
Your Threshold: $150 ✅

[EMBEDDED PRICE CHART]

🎫 Buy Now: https://ticketmaster.com/event/123456789
```

### Daily Summary Email Format
```
Daily Ticket Price Summary - Aug 26, 2025

🎵 Taylor Swift - MetLife Stadium
Current Price: $180 (↓ 12% from yesterday)
Your Threshold: $150
[EMBEDDED PRICE CHART]
🎫 Buy Now: https://ticketmaster.com/event/123...

🎵 Coldplay - Madison Square Garden  
Current Price: $95 (↑ 5% from yesterday)
Your Threshold: $75
[EMBEDDED PRICE CHART]
🎫 Buy Now: https://ticketmaster.com/event/456...
```

### Graph Features
- Line chart showing 30-day price trends
- Different colors for ticket sections/types
- Horizontal line indicating price threshold
- Highlight current price and percentage changes
- Generated as PNG images embedded in HTML emails

## API Integration

### Ticketmaster API
- **Free tier**: 5,000 requests/day
- **Rate limiting**: Implement caching (15-30 minutes)
- **Endpoints**: Discovery API for event details and pricing
- **Fallback**: Web scraping with BeautifulSoup (respectful)

### Rate Limiting Strategy
- Cache API responses for 30 minutes
- Check prices every 2 hours (configurable)
- Batch multiple concert checks in single session
- Intelligent polling (more frequent closer to event dates)

## Deployment Options

### Recommended: GitHub Codespaces
- **Cost**: Free (60 hours/month)
- **Setup**: Push to GitHub, open in Codespaces
- **Execution**: Run `python main.py` continuously
- **Reliability**: Cloud-based, always-on capability

### Alternative: Local Machine
- **Cost**: Free
- **Setup**: Cron job scheduling
- **Execution**: `0 */2 * * * cd /path/to/tracker && python main.py`
- **Reliability**: Depends on local machine uptime

### Backup: Replit
- **Cost**: Free tier available
- **Setup**: Upload code, enable "Always On"
- **Execution**: Web-based management
- **Reliability**: Good for testing/development

## Security Considerations
- Store API keys in environment variables
- Use Gmail App Passwords (not main password)
- No sensitive data in config.ini (use .env)
- Respect Ticketmaster robots.txt and terms of service

## Development Timeline
- **Day 1**: Basic API integration and database setup
- **Day 2**: Email notifications and price tracking logic
- **Day 3**: Graph generation and email formatting
- **Day 4**: Testing, configuration, and deployment

## Maintenance
- **Adding concerts**: Edit config.ini and restart script
- **Removing concerts**: Remove from config.ini and restart
- **Price thresholds**: Update values in config.ini
- **Database cleanup**: Automatic 90-day price history retention

## Cost Breakdown
- **Hosting**: $0 (GitHub Codespaces free tier)
- **Database**: $0 (SQLite local file)
- **Email**: $0 (Gmail SMTP)
- **API**: $0 (Ticketmaster free tier)
- **Total**: $0/month

## Success Metrics
- Reliable price tracking (>95% uptime)
- Email delivery success rate (>99%)
- Price drop detection accuracy
- User satisfaction (single user - you!)