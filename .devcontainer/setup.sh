#!/bin/bash

set -e  # Exit on error

echo "🔧 Setting up TixScanner development environment..."

# Verify pre-installed browser and driver (should be in Selenium image)
echo "🔍 Checking pre-installed browser and driver..."

# Check for Chromium (should be pre-installed in selenium/standalone-chromium image)
if command -v chromium &> /dev/null; then
    echo "✅ Chromium found:"
    chromium --version
    # Create compatibility symlinks for the code
    sudo ln -sf /usr/bin/chromium /usr/bin/google-chrome 2>/dev/null || true
    sudo ln -sf /usr/bin/chromium /usr/bin/chromium-browser 2>/dev/null || true
elif command -v google-chrome &> /dev/null; then
    echo "✅ Chrome found:"
    google-chrome --version
else
    echo "❌ No browser found in Selenium image - this shouldn't happen!"
    exit 1
fi

# Check for ChromeDriver (should be pre-installed)
if command -v chromedriver &> /dev/null; then
    echo "✅ ChromeDriver found:"
    chromedriver --version
    # Ensure it's in the expected location
    sudo ln -sf $(which chromedriver) /usr/local/bin/chromedriver 2>/dev/null || true
else
    echo "❌ ChromeDriver not found in Selenium image - this shouldn't happen!"
    exit 1
fi

# Update and install packages
echo "🐍 Setting up Python and Git..."
apt-get update -qq
apt-get install -y python3-pip python3-venv git
pip install --upgrade pip --break-system-packages

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --no-cache-dir --break-system-packages -r requirements.txt

# Set up git for automated backups
echo "🔧 Configuring git for automated backups..."
git config --global user.email "tixscanner@codespaces.github" || true
git config --global user.name "TixScanner Auto-Backup" || true

echo "✨ Development environment setup complete!"
echo ""
echo "🎯 Ready to run TixScanner:"
echo "   python3 main.py --mode check    # Test run"
echo "   python3 main.py                 # Continuous monitoring"