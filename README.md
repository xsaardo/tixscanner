# TixScanner - Ticket Price Tracking Application

A Python application that monitors concert ticket prices via the Ticketmaster API and sends email notifications when prices drop below your specified thresholds.

## Features

- **Real-time Price Monitoring**: Track ticket prices for your favorite concerts
- **Smart Alerts**: Get notified when prices drop below your thresholds
- **Daily Summaries**: Receive daily email reports with price trends and graphs
- **Price History**: Store and analyze 30+ days of pricing data
- **Automated Cleanup**: Automatically manages old data (90+ days)
- **Local Database**: All data stored locally in SQLite for privacy

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Gmail account with App Password enabled
- Ticketmaster API key (free at [developer.ticketmaster.com](https://developer.ticketmaster.com/))

### Installation

1. **Clone/Download** the project to your local machine

2. **Set up virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the application**:
   - Copy `config.ini.example` to `config.ini`
   - Copy `.env.example` to `.env`
   - Fill in your API keys and email settings (see Configuration section)

5. **Initialize database**:
   ```bash
   python -c "from src.database import initialize_database; initialize_database()"
   ```

6. **Run the application**:
   ```bash
   python main.py
   ```

## Configuration

### Environment Variables (.env)

```bash
# Ticketmaster API key (get from developer.ticketmaster.com)
TICKETMASTER_API_KEY=your_api_key_here

# Gmail credentials (use App Password, not regular password)
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password
```

### Application Settings (config.ini)

```ini
[api]
ticketmaster_key = your_api_key_here

[email]
gmail_user = your.email@gmail.com
gmail_password = your_app_password_here
recipient = your.email@gmail.com

[monitoring]
# How often to check prices (hours)
check_frequency_hours = 2
# When to send daily summary (24h format)
daily_summary_time = 09:00
# Minimum price drop % to trigger alert
minimum_price_drop_percent = 10

[concerts]
# Add events to track: event_id = price_threshold
1700630C79D40EAD = 500.00
```

### Finding Event IDs

1. Go to [Ticketmaster.com](https://www.ticketmaster.com)
2. Find your concert and copy the event URL
3. Extract the event ID from the URL (usually after `/event/`)
4. Add it to the `[concerts]` section in `config.ini`

## 🔐 Secure Gmail Setup (OAuth2 - Recommended)

**⚠️ App Passwords are deprecated and insecure. Use OAuth2 instead!**

### Quick Setup (5 minutes):
1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project: "TixScanner Email"

2. **Enable Gmail API**:
   - Go to "APIs & Services" → "Library" 
   - Search "Gmail API" → Enable

3. **Create OAuth2 Credentials**:
   - Go to "APIs & Services" → "Credentials"
   - Click "CREATE CREDENTIALS" → "OAuth client ID"
   - Configure consent screen (External, App name: "TixScanner")
   - Application type: "Desktop application"
   - Download credentials as `gmail_credentials.json`

4. **First Run Authentication**:
   ```bash
   python test_email_setup.py
   ```
   - Browser will open for Gmail sign-in
   - Grant email sending permissions
   - Tokens saved automatically for future use

### Security Benefits:
- ✅ **No passwords stored** - Uses secure OAuth2 tokens
- ✅ **Granular permissions** - Only email sending access
- ✅ **Automatic refresh** - Tokens refresh seamlessly
- ✅ **Revokable access** - Can revoke anytime in Google settings

## Usage

### Command Line

```bash
# Run once to check prices now
python main.py

# Run with specific config file
python main.py --config /path/to/config.ini

# Run tests
python -m pytest

# Check database status
python -c "from src.database import get_database_stats; print(get_database_stats())"
```

### Adding Concerts to Track

Edit `config.ini` and add concert entries:

```ini
[concerts]
# Format: ticketmaster_event_id = max_price_threshold
1700630C79D40EAD = 500.00
G5v0Z9H7B-kZb = 150.00
```

### Email Notifications

**Price Alert Example**:
```
🚨 Price Drop Alert!

Taylor Swift - MetLife Stadium
New Price: $140 (↓ 15% from $165)
Your Threshold: $150 ✅

[Price History Graph]

🎫 Buy Now: https://ticketmaster.com/event/123...
```

**Daily Summary Example**:
```
📊 Daily Ticket Price Summary - Dec 25, 2024

🎵 Taylor Swift - MetLife Stadium
Current: $180 (↓ 12% from yesterday)
Threshold: $150
[Price Graph]
🎫 https://ticketmaster.com/event/123...
```

## Project Structure

```
tixscanner/
├── main.py                 # Application entry point
├── config.ini             # Your configuration
├── .env                   # API keys and credentials
├── requirements.txt       # Python dependencies
├── tickets.db            # SQLite database (auto-created)
├── src/
│   ├── database.py       # Database management
│   ├── models.py         # Data models
│   └── db_operations.py  # CRUD operations
├── tests/                # Test suite
└── logs/                # Application logs
```

## Database Management

### View Statistics
```python
from src.database import get_database_stats
print(get_database_stats())
```

### Backup Database
```python
from src.database import backup_database
backup_database()  # Creates timestamped backup
```

### Export Data
```python
from src.db_operations import export_data
import json

data = export_data()
with open('backup.json', 'w') as f:
    json.dump(data, f, indent=2)
```

### Reset Database (⚠️ Deletes all data!)
```python
from src.database import reset_database
reset_database()
```

## Development

### Running Tests
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src

# Run specific test file
python -m pytest tests/test_database.py -v
```

### Code Style
- Uses type hints throughout
- Follows PEP 8 conventions
- Comprehensive error handling
- Structured logging

### Adding Features

1. **New API endpoints**: Extend `src/api_client.py`
2. **Email templates**: Modify `src/email_service.py`
3. **Data models**: Add to `src/models.py`
4. **Database operations**: Extend `src/db_operations.py`

## Troubleshooting

### Common Issues

**"Failed to connect to database"**
- Check file permissions in the project directory
- Ensure SQLite is available (built into Python)

**"Authentication failed" (Email)**
- Verify you're using Gmail App Password, not regular password
- Check 2-Factor Authentication is enabled
- Ensure App Password has no spaces

**"API key invalid" (Ticketmaster)**
- Verify API key at [developer.ticketmaster.com](https://developer.ticketmaster.com/)
- Check for extra spaces or characters
- Ensure you're within API rate limits (5000 requests/day)

**"No price data found"**
- Verify event ID is correct
- Check if event has resale tickets available
- Some events may not have dynamic pricing

### Logging

Logs are stored in `logs/tixscanner.log`:
```bash
# View recent logs
tail -f logs/tixscanner.log

# Search for errors
grep ERROR logs/tixscanner.log
```

### Support

For issues or questions:
1. Check the logs in `logs/tixscanner.log`
2. Verify configuration in `config.ini`
3. Test database with: `python -c "from src.database import check_database_integrity; print(check_database_integrity())"`

## Security Notes

- **Never commit** `.env` or `config.ini` files to version control
- **Use App Passwords** for Gmail, never your main password
- **API keys** are stored locally only
- **Database** is local SQLite file, no cloud storage

## Cost

- **Ticketmaster API**: Free (5000 requests/day)
- **Gmail SMTP**: Free
- **Storage**: Local only
- **Hosting**: Optional (GitHub Codespaces free tier available)

## License

This project is for personal use only. Respect Ticketmaster's terms of service and rate limits.