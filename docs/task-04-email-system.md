# Task 4: Email System with Charts

## Overview
Implement the email notification system that sends price alerts and daily summaries with embedded price charts using Gmail SMTP and matplotlib for chart generation.

## Acceptance Criteria
- [ ] Email client is configured and working with Gmail SMTP
- [ ] Price charts are generated using matplotlib
- [ ] HTML emails with embedded charts are sent successfully
- [ ] Both price alerts and daily summaries are implemented
- [ ] Email templates are responsive and well-formatted
- [ ] Email delivery is logged and tracked

## Implementation Steps

### 1. Email Client Setup
- [ ] Create `src/email_client.py` module
- [ ] Implement Gmail SMTP configuration:
  - [ ] SMTP server connection (smtp.gmail.com:587)
  - [ ] Authentication with app password
  - [ ] TLS encryption setup
  - [ ] Connection testing function
- [ ] Load email credentials from environment variables
- [ ] Implement connection pooling for multiple emails

### 2. Chart Generation System
- [ ] Create `src/chart_generator.py` module
- [ ] Implement price trend charts:
  - [ ] Line chart for price history over time
  - [ ] Highlight current price and threshold line
  - [ ] Color coding for price increases/decreases
  - [ ] Multiple ticket sections on same chart
- [ ] Chart styling and formatting:
  - [ ] Professional color scheme
  - [ ] Clear axis labels and legends
  - [ ] Responsive sizing for email embedding
  - [ ] High DPI for crisp display
- [ ] Chart data processing:
  - [ ] Handle missing data points gracefully
  - [ ] Smooth price trend lines
  - [ ] Percentage change annotations

### 3. Email Template System
- [ ] Create `src/email_templates.py` module
- [ ] Design HTML email templates:
  - [ ] Responsive design for mobile and desktop
  - [ ] Professional styling with CSS
  - [ ] Consistent branding and layout
  - [ ] Fallback plain text versions
- [ ] Implement template variables:
  - [ ] Dynamic content insertion
  - [ ] Concert information placeholders
  - [ ] Price change calculations
  - [ ] Chart image embeddings

### 4. Price Alert Emails
- [ ] Implement immediate price drop alerts:
  - [ ] `send_price_alert(event_id: str, old_price: float, new_price: float)`
  - [ ] Calculate percentage price drop
  - [ ] Include current vs threshold price comparison
  - [ ] Embed relevant price chart
  - [ ] Add direct purchase link
- [ ] Alert email content:
  - [ ] Clear subject line with price drop amount
  - [ ] Concert name and venue information
  - [ ] Price change details and percentages
  - [ ] Trend chart showing recent price history
  - [ ] Call-to-action button for purchasing

### 5. Daily Summary Emails
- [ ] Implement daily price summary:
  - [ ] `send_daily_summary()`
  - [ ] Aggregate all tracked concerts
  - [ ] Show price changes from previous day
  - [ ] Include 7-day trend charts for each concert
  - [ ] Highlight concerts near threshold prices
- [ ] Summary email content:
  - [ ] Overview of all tracked concerts
  - [ ] Price change summary table
  - [ ] Individual charts for each concert
  - [ ] Purchase links for all concerts
  - [ ] Subscription management options

### 6. Chart Integration
- [ ] Implement chart embedding in emails:
  - [ ] Generate charts as PNG files
  - [ ] Convert images to base64 for embedding
  - [ ] Optimize image size for email delivery
  - [ ] Handle chart generation errors gracefully
- [ ] Chart customization:
  - [ ] Different chart types (line, bar, candlestick)
  - [ ] Configurable time ranges (7 days, 30 days)
  - [ ] Theme options (light/dark)
  - [ ] Custom color schemes per concert

### 7. Email Delivery Management
- [ ] Implement email queuing system:
  - [ ] Queue emails for batch sending
  - [ ] Retry failed email deliveries
  - [ ] Rate limiting for Gmail SMTP
  - [ ] Priority handling (alerts vs summaries)
- [ ] Delivery tracking:
  - [ ] Log all email attempts
  - [ ] Track delivery success/failure rates
  - [ ] Monitor bounce rates
  - [ ] Error reporting and alerting

### 8. Configuration Integration
- [ ] Email configuration options:
  - [ ] Recipient email address
  - [ ] Sender name and email
  - [ ] Email frequency settings
  - [ ] Chart preferences
  - [ ] Template customization options
- [ ] User preference management:
  - [ ] HTML vs plain text preference
  - [ ] Chart types and styles
  - [ ] Email frequency (immediate, hourly, daily)
  - [ ] Opt-out mechanisms

## Testing Criteria
- [ ] Gmail SMTP connection works correctly
- [ ] Price charts generate without errors
- [ ] HTML emails render properly in major clients
- [ ] Images are embedded correctly in emails
- [ ] Price alert emails are sent immediately
- [ ] Daily summaries are formatted correctly
- [ ] Email delivery is logged accurately
- [ ] Failed emails are retried appropriately

## Files to Create
- `src/email_client.py` - Gmail SMTP client
- `src/chart_generator.py` - Matplotlib chart creation
- `src/email_templates.py` - HTML/text templates
- `templates/price_alert.html` - Alert email template
- `templates/daily_summary.html` - Summary email template
- `tests/test_email_system.py` - Email system tests
- `tests/test_chart_generator.py` - Chart generation tests

## Dependencies
- Task 1: Project Setup (for configuration)
- Task 2: Database Schema (for price history data)
- `matplotlib` library
- `smtplib` (built-in)
- `email.mime` (built-in)
- Gmail app password

## Estimated Time
5-7 hours

## Notes
- Use Gmail app passwords, not regular account passwords
- Test email rendering across different clients (Gmail, Outlook, Apple Mail)
- Keep embedded images under 500KB each for deliverability
- Implement proper error handling for SMTP failures
- Consider email rate limits (Gmail: ~500 emails/day)
- Include unsubscribe options even for personal use

## Chart Specifications
```python
# Chart dimensions and styling
CHART_WIDTH = 800
CHART_HEIGHT = 400
DPI = 150
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
```

## Sample Email Templates

### Price Alert Subject
```
🎫 Price Drop: {concert_name} - Now ${new_price} (↓{percentage}%)
```

### Daily Summary Subject
```
📊 Daily Price Update - {date} ({num_concerts} concerts tracked)
```

## Sample Usage
```python
# Example usage after implementation
from src.email_client import EmailClient
from src.chart_generator import generate_price_chart

# Send price alert
email_client = EmailClient()
chart_path = generate_price_chart("123456789", days=7)
email_client.send_price_alert("123456789", 200.0, 150.0, chart_path)

# Send daily summary
email_client.send_daily_summary()
```