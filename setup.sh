#!/bin/bash
# Setup script for Shorts Studio
set -e

echo "=== Shorts Studio Setup ==="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required. Install from https://www.python.org/downloads/"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python: $PY_VERSION"

# Check ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "ERROR: ffmpeg is required."
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu: sudo apt install ffmpeg"
    exit 1
fi
echo "ffmpeg: $(ffmpeg -version | head -1)"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Create directories
echo ""
echo "Creating directories..."
mkdir -p data/content/sources
mkdir -p data/content/sources/downloaded
mkdir -p data/content/sources/stock
mkdir -p data/output
mkdir -p data/work
mkdir -p secrets

# Make launcher executable
chmod +x shorts

# Install launcher to PATH
if [ -d "$HOME/.local/bin" ]; then
    ln -sf "$(pwd)/shorts" "$HOME/.local/bin/shorts"
    echo "Launcher installed to ~/.local/bin/shorts"
else
    mkdir -p "$HOME/.local/bin"
    ln -sf "$(pwd)/shorts" "$HOME/.local/bin/shorts"
    echo "Launcher installed to ~/.local/bin/shorts"
    echo "Add ~/.local/bin to your PATH if not already there."
fi

# Check deps
echo ""
echo "Verifying dependencies..."
PYTHONPATH=src python3 -m shorts_studio.cli.main check-deps

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Run: shorts status"
echo "  2. Run: shorts dashboard  (opens web UI at http://127.0.0.1:8765)"
echo "  3. Drop a video in data/content/sources/ and run: shorts run --allow-unverified"
echo ""
echo "Optional:"
echo "  - Get a free Pexels API key: https://www.pexels.com/api/"
echo "  - Set up YouTube OAuth: see README.md"
echo "  - Generate audio assets: python3 gen_audio.py"