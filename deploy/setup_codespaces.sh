#!/bin/bash
# Setup script for GitHub Codespaces deployment

set -e  # Exit on any error

echo "🚀 Setting up TixScanner in GitHub Codespaces..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the project root."
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Chrome for web scraping (required for Selenium)
echo "🌐 Installing Google Chrome for web scraping..."
if ! command -v google-chrome &> /dev/null; then
    # Update package list
    sudo apt-get update

    # Install wget if not available
    sudo apt-get install -y wget

    # Download and install Chrome
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
    sudo apt-get update
    sudo apt-get install -y google-chrome-stable

    # Verify installation
    if command -v google-chrome &> /dev/null; then
        echo "✅ Chrome installed successfully"
        google-chrome --version
    else
        echo "❌ Chrome installation failed"
    fi
else
    echo "✅ Chrome already installed"
    google-chrome --version
fi

# Check if database exists, if not, initialize it
if [ ! -f "tickets.db" ]; then
    echo "🗄️  Database not found locally, attempting to restore from git..."
    git pull origin main || echo "ℹ️  Could not pull from remote (this is normal for new setups)"
fi

# Check for required environment variables
if [ -z "$GMAIL_TOKEN_JSON" ]; then
    echo "⚠️  Warning: GMAIL_TOKEN_JSON environment variable not set."
    echo "   You'll need to set this in GitHub Codespaces secrets for email functionality."
    echo "   See CODESPACES.md for detailed setup instructions."
fi

# Test git configuration
echo "🔧 Configuring git for automated backups..."
git config --global user.email "tixscanner@codespaces.github" 2>/dev/null || true
git config --global user.name "TixScanner Auto-Backup" 2>/dev/null || true

# Test database backup system
echo "🧪 Testing database backup system..."
python3 -c "
from src.git_backup import GitDatabaseBackup
import logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise

backup = GitDatabaseBackup()
if backup.check_git_availability():
    backup.configure_git_for_codespaces()
    print('✅ Git backup system configured successfully')
else:
    print('❌ Git backup system configuration failed')
" || echo "⚠️  Git backup test failed (may work in actual Codespaces environment)"

echo ""
echo "🎯 Setup completed! Here's how to run TixScanner:"
echo ""
echo "   For continuous monitoring (recommended):"
echo "   $ screen -S tixscanner"
echo "   $ python3 main.py"
echo "   # Press Ctrl+A, then D to detach from screen"
echo ""
echo "   For single price check:"
echo "   $ python3 main.py --mode check"
echo ""
echo "   For daily summary only:"
echo "   $ python3 main.py --mode summary"
echo ""

# Check if we're actually in Codespaces
if [ -n "$CODESPACES" ]; then
    echo "🌟 Running in GitHub Codespaces environment"
    echo "   Database will be automatically backed up to git daily at midnight"
    echo "   Check logs with: tail -f logs/tixscanner.log"
else
    echo "🖥️  Running in local environment"
    echo "   Consider using GitHub Codespaces for always-on monitoring"
fi

echo ""
echo "📖 For more information, see:"
echo "   - CODESPACES.md (deployment guide)"
echo "   - docs/task-06-scheduling-deployment.md (full documentation)"
echo ""
echo "✨ Happy ticket tracking!"