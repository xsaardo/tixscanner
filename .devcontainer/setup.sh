#!/bin/bash

echo "🔧 Setting up TixScanner development environment..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Chrome
echo "🌐 Installing Google Chrome..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update
sudo apt-get install -y google-chrome-stable

# Verify Chrome installation
if command -v google-chrome &> /dev/null; then
    echo "✅ Chrome installed successfully"
    google-chrome --version
else
    echo "❌ Chrome installation failed"
    exit 1
fi

# Set up git for automated backups
echo "🔧 Configuring git for automated backups..."
git config --global user.email "tixscanner@codespaces.github" || true
git config --global user.name "TixScanner Auto-Backup" || true

echo "✨ Development environment setup complete!"
echo ""
echo "🎯 Ready to run TixScanner:"
echo "   python3 main.py --mode check    # Test run"
echo "   python3 main.py                 # Continuous monitoring"