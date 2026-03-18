#!/bin/bash
#
# Quick setup script for Butlerclaw development environment
#
# Usage:
#   ./scripts/setup.sh
#

set -e

echo "🚀 Setting up Butlerclaw development environment..."

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Found Python $python_version"

# Check if Python 3.8+
required_version="3.8"
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    echo "❌ Python 3.8 or higher is required"
    exit 1
fi
echo "✓ Python version is compatible"

# Check for tkinter
echo "📋 Checking tkinter..."
if python3 -c "import tkinter" 2>/dev/null; then
    echo "✓ tkinter is available"
else
    echo "❌ tkinter is not installed"
    echo "  Please install tkinter for your system:"
    echo "    Ubuntu/Debian: sudo apt install python3-tk"
    echo "    Fedora: sudo dnf install python3-tkinter"
    echo "    macOS: brew install python-tk"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt -q
echo "✓ Dependencies installed"

# Install development dependencies
echo "📥 Installing development dependencies..."
pip install -r requirements-dev.txt -q
echo "✓ Development dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Butlerclaw Development Environment
DEBUG=true
LOG_LEVEL=debug
EOF
    echo "✓ .env file created"
fi

# Run tests to verify setup
echo "🧪 Running tests to verify setup..."
if python -m pytest tests/ -v --tb=short 2>/dev/null; then
    echo "✓ All tests passed"
else
    echo "⚠️  Some tests failed (this is OK for initial setup)"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run the application: python openclaw_assistant.py"
echo "  3. Run tests: pytest tests/"
echo ""
