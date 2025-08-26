# Development Context
- use @docs/specs.md for current status and next steps

# Bash commands
- python main.py: Run the ticket tracker
- python -m pytest: Run tests (when implemented)
- pip install -r requirements.txt: Install dependencies

# Code style
- Use type hints for all function parameters and returns
- Follow PEP 8 style guidelines
- Use descriptive variable names (e.g., `ticket_price` not `tp`)
- Add docstrings to all functions and classes
- Keep functions focused and under 50 lines when possible

# Configuration
- Store sensitive data (API keys, passwords) in .env file only
- Use config.ini for user preferences and concert tracking
- Never commit .env files to git
- Use meaningful section names in config.ini

# Error Handling
- Always wrap API calls in try-catch blocks
- Log errors to both console and file
- Implement retry logic for transient API failures
- Gracefully handle network timeouts and rate limits

# Data Management
- Store at least 30 days of price history for trend analysis
- Clean up old data automatically (90+ days)
- Backup SQLite database before major updates
- Use transactions for multi-table operations

# Email Best Practices
- Test email formatting in both HTML and plain text
- Limit embedded images to reasonable sizes (<500KB each)
- Use clear subject lines with price alerts vs daily summaries

# API Usage
- Respect Ticketmaster rate limits (5000 requests/day)
- Cache responses for 30 minutes minimum
- Implement exponential backoff for API errors
- Monitor daily API usage to avoid hitting limits

# Workflow
- Test email functionality before deploying
- Verify all concerts are being tracked correctly
- Check database integrity after updates
- Monitor logs for API errors or email delivery failures