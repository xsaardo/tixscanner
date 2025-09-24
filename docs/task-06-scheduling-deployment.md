# Task 6: Scheduling and Deployment

## Overview
Implement the main application entry point with scheduling capabilities, integrate all components, and deploy the application to a hosting platform for continuous operation.

## Acceptance Criteria
- [ ] Main application orchestrates all components correctly
- [ ] Scheduling system runs monitoring and daily summaries automatically
- [ ] Application can run continuously without manual intervention
- [ ] Deployment is successful on chosen platform (GitHub Codespaces/local)
- [ ] Logging and monitoring provide visibility into system operation
- [ ] Application recovers gracefully from failures

## Implementation Steps

### 1. Main Application Structure
- [ ] Create `main.py` as the primary entry point
- [ ] Implement application orchestration:
  - [ ] Initialize all components (database, API client, email system)
  - [ ] Handle application startup and shutdown
  - [ ] Coordinate between different modules
  - [ ] Manage application state and lifecycle
- [ ] Command line interface:
  - [ ] Support for different run modes (continuous, one-time check, test)
  - [ ] Configuration validation and setup assistance
  - [ ] Debug and verbose logging options

### 2. Scheduling System Implementation
- [x] Implement automated scheduling:
  - [x] Use custom threading-based scheduler (MonitoringScheduler)
  - [x] Configure price monitoring frequency (every 2 hours default)
  - [x] Schedule daily summary emails (9 AM default)
  - [x] Background task management with graceful shutdown
- [x] Schedule configuration:
  - [x] Load schedule settings from config.ini
  - [x] Support for different time zones
  - [x] Flexible scheduling patterns (configurable intervals)
  - [x] Schedule validation and error handling
- [ ] **NEW: Database persistence for Codespaces:**
  - [ ] Implement git-based database backup system
  - [ ] Schedule automatic database commits (daily at midnight)
  - [ ] Handle git authentication in Codespaces environment
  - [ ] Database restoration on Codespace startup

### 3. Application Integration
- [ ] Integrate all components:
  - [ ] Database initialization and connection management
  - [ ] API client initialization with rate limiting
  - [ ] Email system setup and testing
  - [ ] Price monitoring engine integration
- [ ] Cross-component communication:
  - [ ] Shared configuration across modules
  - [ ] Event-driven communication for alerts
  - [ ] Error propagation and handling
  - [ ] Resource sharing and cleanup

### 4. Logging and Monitoring System
- [ ] Implement comprehensive logging:
  - [ ] Configure Python logging with appropriate levels
  - [ ] File-based logging with rotation
  - [ ] Console output for development
  - [ ] Structured logging for better analysis
- [ ] Application monitoring:
  - [ ] Health checks for all components
  - [ ] Performance metrics collection
  - [ ] Error tracking and alerting
  - [ ] Resource usage monitoring (memory, CPU)

### 5. Configuration Management
- [ ] Enhanced configuration system:
  - [ ] Configuration validation on startup
  - [ ] Environment-specific configurations
  - [ ] Configuration hot-reloading (optional)
  - [ ] Default configuration generation
- [ ] Setup assistance:
  - [ ] Configuration wizard for first-time setup
  - [ ] API key validation
  - [ ] Email configuration testing
  - [ ] Database initialization scripts

### 6. Error Handling and Recovery
- [ ] System-wide error handling:
  - [ ] Graceful error recovery for all components
  - [ ] Automatic restart mechanisms
  - [ ] Error notification system
  - [ ] Fallback modes for degraded operation
- [ ] Application resilience:
  - [ ] Circuit breaker pattern for external services
  - [ ] Timeout handling for long-running operations
  - [ ] Resource leak prevention
  - [ ] Clean shutdown procedures

### 7. Deployment Preparation
- [ ] Prepare for deployment:
  - [ ] Create comprehensive requirements.txt
  - [ ] Environment setup documentation
  - [ ] Deployment scripts and instructions
  - [ ] Configuration templates and examples
- [ ] Platform-specific preparation:
  - [ ] GitHub Codespaces configuration
  - [ ] Local machine deployment guide
  - [ ] Docker containerization (optional)
  - [ ] Environment variable management

### 8. Testing and Validation
- [ ] End-to-end testing:
  - [ ] Full application workflow testing
  - [ ] Integration testing across all components
  - [ ] Performance testing under load
  - [ ] Error scenario testing
- [ ] Deployment validation:
  - [ ] Test deployment on target platform
  - [ ] Verify all scheduled jobs run correctly
  - [ ] Validate email delivery in production environment
  - [ ] Monitor system behavior over time

### 9. Production Deployment

#### Primary: GitHub Codespaces Deployment
- [ ] **Pre-deployment setup:**
  - [ ] Update .gitignore to include tickets.db in repository
  - [ ] Run local OAuth flow and extract tokens using extract_gmail_tokens.py
  - [ ] Configure GitHub Codespaces secrets (GMAIL_TOKEN_JSON)
  - [ ] Enable continuous monitoring in main.py (uncomment scheduler lines)

- [ ] **Deploy to GitHub Codespaces:**
  - [ ] Push code with database to GitHub repository
  - [ ] Create Codespace from repository
  - [ ] Verify environment variables are loaded automatically
  - [ ] Install dependencies: pip install -r requirements.txt
  - [ ] Start application with screen: screen -S tixscanner && python main.py
  - [ ] Verify scheduler starts and database persistence works

- [ ] **Validation and monitoring:**
  - [ ] Test price check execution (should run every 2 hours)
  - [ ] Test daily summary email (9 AM)
  - [ ] Verify database commits to git automatically
  - [ ] Monitor Codespaces resource usage (should stay under 25 hours/month)

#### Alternative: Local Machine Deployment
- [ ] Local machine cron job setup (fallback option)
- [ ] Container deployment configuration (Docker option)
- [ ] Process monitoring setup (systemd/supervisor)

### 10. Post-Deployment Monitoring
- [ ] Monitor deployed application:
  - [ ] Verify scheduled jobs are running
  - [ ] Check log files for errors
  - [ ] Validate email delivery
  - [ ] Monitor API usage and rate limits
- [ ] Ongoing maintenance:
  - [ ] Log rotation and cleanup
  - [ ] Database maintenance and backups
  - [ ] Performance optimization
  - [ ] Security updates and patches

## Testing Criteria
- [ ] Application starts up without errors
- [ ] All scheduled jobs execute at correct times
- [ ] Price monitoring detects changes and sends alerts
- [ ] Daily summaries are generated and sent
- [ ] System recovers from various failure scenarios
- [ ] Logging provides adequate visibility
- [ ] Deployment platform runs application continuously
- [ ] Resource usage remains within acceptable limits
- [ ] **Database persistence works correctly:**
  - [ ] Database survives Codespace restarts
  - [ ] Automatic git commits happen daily
  - [ ] Price history is preserved across sessions
  - [ ] No data loss during normal operation

## Files to Create/Update

### Already Implemented
- ✅ `main.py` - Main application entry point (needs scheduler activation)
- ✅ `src/scheduler.py` - Scheduling logic and job management
- ✅ `src/config_manager.py` - Application configuration management
- ✅ `requirements.txt` - Production dependencies
- ✅ `CODESPACES.md` - Codespaces deployment guide

### New Files Needed for Database Persistence
- `src/git_backup.py` - Git-based database backup system
- `deploy/setup_codespaces.sh` - Automated Codespaces setup script
- `tests/test_persistence.py` - Database persistence integration tests

### Files to Update
- `.gitignore` - Include tickets.db for persistence
- `main.py` - Enable scheduler by default for production
- `src/scheduler.py` - Add database backup scheduling
- `src/database.py` - Add git backup integration

## Dependencies
- All previous tasks (1-5)
- `schedule` library
- Target deployment platform access

## Estimated Time
3-5 hours

## Notes
- Implement graceful shutdown to handle interruption signals
- Use logging instead of print statements for production deployment
- Consider implementing health check endpoints for monitoring
- Document all configuration options clearly
- Test the deployment process thoroughly before going live

## Main Application Structure
```python
# main.py structure overview
def main():
    # 1. Load and validate configuration
    # 2. Initialize logging
    # 3. Initialize database and components
    # 4. Set up scheduled jobs
    # 5. Start monitoring loop
    # 6. Handle shutdown gracefully

if __name__ == "__main__":
    main()
```

## Scheduling Configuration
```ini
[scheduling]
price_check_frequency = "every(2).hours"
daily_summary_time = "09:00"
timezone = "America/New_York"
enable_weekend_checks = true
```

## Deployment Options

### GitHub Codespaces (Recommended)

**Why Codespaces:**
- ✅ **Free tier**: 120 core hours/month (sufficient for 2-hour monitoring cycles)
- ✅ **Zero infrastructure setup**: Instant deployment
- ✅ **Cloud reliability**: No dependency on local machine uptime
- ✅ **Gmail OAuth integration**: Environment variable support configured
- ✅ **Resource efficiency**: Scheduler sleeps between checks, using ~25 hours/month

**Resource Usage Analysis:**
- Price checks (every 2h): ~12 hours/month
- Daily summaries: ~1 hour/month
- Scheduler overhead: ~10 hours/month
- **Total: ~25 hours/month** (well under 120-hour free limit)

```bash
# In codespaces terminal
pip install -r requirements.txt

# For continuous monitoring (recommended)
screen -S tixscanner
python main.py  # Runs with scheduler enabled
# Ctrl+A, D to detach from screen

# Alternative: One-time runs
python main.py --mode check     # Single price check
python main.py --mode summary   # Send daily summary only
```

### Local Machine with Cron (Alternative)
```bash
# Add to crontab for scheduled runs
0 */2 * * * cd /path/to/tixscanner && python main.py --mode check
0 9 * * * cd /path/to/tixscanner && python main.py --mode summary
```

**Limitations:**
- ❌ Requires always-on local machine
- ❌ No automatic recovery from power/network issues
- ❌ Manual cron job configuration required

## Database Persistence Strategy

**Challenge:** Codespaces filesystem is ephemeral - data is lost when Codespace stops.

**Solution:** Git-based database persistence (recommended for this use case)

**Why Git-based persistence:**
- ✅ **Size manageable**: SQLite database ~1-2 MB over time
- ✅ **Zero additional cost**: Uses existing GitHub repository
- ✅ **Version control**: Track data changes over time
- ✅ **Automatic backup**: Integrated with scheduler
- ✅ **Disaster recovery**: Easy to restore from any commit

**Implementation approach:**
1. Include `tickets.db` in Git repository (remove from .gitignore)
2. Add automatic database backup to scheduler (daily at midnight)
3. Commit and push database changes automatically
4. On Codespace restart, database is restored from latest commit

**Alternative options considered:**
- Cloud databases (Supabase/PlanetScale): Requires significant code changes
- File storage services (Drive/Dropbox): Additional API complexity
- GitHub Releases: Good for backups, not real-time sync

## Sample Usage
```python
# Command line usage examples
python main.py                          # Run continuously
python main.py --mode check            # One-time price check
python main.py --mode summary          # Send daily summary
python main.py --mode test             # Test all components
python main.py --config custom.ini     # Use custom config
python main.py --verbose               # Enable debug logging
```

## Production Monitoring Commands
```bash
# Check application status
ps aux | grep main.py

# View recent logs
tail -f logs/tixscanner.log

# Check email delivery logs
grep "Email sent" logs/tixscanner.log | tail -20

# Monitor API usage
grep "API request" logs/tixscanner.log | wc -l
```