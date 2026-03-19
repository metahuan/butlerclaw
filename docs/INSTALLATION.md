# Installation Guide

This guide covers various methods to install Butlerclaw on your system.

## Table of Contents

- [System Requirements](#system-requirements)
- [Pre-built Executables](#pre-built-executables)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
- [Installing from Source](#installing-from-source)
- [Post-Installation](#post-installation)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **Operating System:**
  - Windows 10/11 (64-bit)
  - macOS 10.15 (Catalina) or later
  - Ubuntu 20.04 / Debian 11 / Fedora 34 or equivalent
- **RAM:** 4 GB minimum, 8 GB recommended
- **Storage:** 500 MB free space
- **Internet:** Required for initial setup and updates

### Python Requirements (Source Installation)

- Python 3.8 or higher
- tkinter support

## Pre-built Executables

### Windows

1. Download `Butlerclaw-Windows.exe` from the [releases page](https://github.com/metahuan/butlerclaw/releases)
2. Double-click the downloaded file to run
3. Windows may show a SmartScreen warning - click "More info" and "Run anyway"
4. The application will start automatically

**Alternative: Using Command Line**

```powershell
# Download using PowerShell
Invoke-WebRequest -Uri "https://github.com/metahuan/butlerclaw/releases/latest/download/Butlerclaw-Windows.exe" -OutFile "Butlerclaw.exe"

# Run the executable
.\Butlerclaw.exe
```

### macOS

1. Download `Butlerclaw-macOS.dmg` from the [releases page](https://github.com/metahuan/butlerclaw/releases)
2. Open the DMG file
3. Drag Butlerclaw to your Applications folder
4. First launch: Right-click the app and select "Open" (required for apps from unidentified developers)

**Using Homebrew (Coming Soon)**

```bash
brew install butlerclaw
```

### Linux

1. Download `Butlerclaw-Linux.tar.gz` from the [releases page](https://github.com/metahuan/butlerclaw/releases)
2. Extract the archive:
   ```bash
   tar -xzf Butlerclaw-Linux.tar.gz
   ```
3. Run the application:
   ```bash
   ./Butlerclaw/butlerclaw
   ```

**Optional: Install System-wide**

```bash
# Extract to /opt
sudo tar -xzf Butlerclaw-Linux.tar.gz -C /opt

# Create symlink
sudo ln -s /opt/Butlerclaw/butlerclaw /usr/local/bin/butlerclaw

# Create desktop entry
sudo tee /usr/share/applications/butlerclaw.desktop > /dev/null <<EOF
[Desktop Entry]
Name=Butlerclaw
Exec=/opt/Butlerclaw/butlerclaw
Icon=/opt/Butlerclaw/icon.png
Type=Application
Categories=Utility;
EOF
```

## Installing from Source

### Prerequisites

Ensure you have Python 3.8+ installed:

```bash
python --version
# or
python3 --version
```

Check tkinter availability:

```bash
python -c "import tkinter; print(tkinter.Tcl().eval('info patchlevel'))"
```

### Step-by-Step Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/metahuan/butlerclaw.git
   cd butlerclaw
   ```

2. **Create Virtual Environment**

   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**

   ```bash
   python openclaw_assistant.py
   ```

### Building from Source

To create your own executable:

```bash
# Install build dependencies
pip install -r requirements-build.txt

# Build executable
# Windows:
python -m PyInstaller OpenClaw龙虾管家.spec --clean

# macOS:
chmod +x build_macos.sh
./build_macos.sh

# Linux:
chmod +x build_linux.sh
./build_linux.sh
```

## Post-Installation

### First Run

1. Launch Butlerclaw
2. Click "Start Installation" button
3. The application will:
   - Check for Node.js (install if missing)
   - Install OpenClaw CLI
   - Prompt for model configuration

### Configuration

Configuration files are stored in:

- **Windows:** `%USERPROFILE%\.openclaw\`
- **macOS/Linux:** `~/.openclaw/`

### Getting API Keys

You'll need API keys for your chosen AI model:

| Provider | Sign Up URL |
|----------|-------------|
| Moonshot (Kimi) | https://platform.moonshot.cn |
| DeepSeek | https://platform.deepseek.com |
| Alibaba (Qwen) | https://dashscope.aliyun.com |
| OpenAI | https://platform.openai.com |
| Anthropic | https://console.anthropic.com |
| Google | https://aistudio.google.com |

## Troubleshooting

### Common Issues

#### "No module named 'tkinter'"

**Windows:**
- Reinstall Python and check "tcl/tk and IDLE" option

**macOS:**
```bash
brew install python-tk
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S python tk
```

#### "Permission denied" on Linux/macOS

```bash
chmod +x butlerclaw
```

#### Application won't start on macOS

1. Open System Preferences → Security & Privacy
2. Click "Open Anyway" next to the Butlerclaw message
3. Or right-click the app and select "Open"

#### Windows Defender/SmartScreen Warning

This is normal for unsigned executables. Click "More info" and "Run anyway" to proceed.

### Getting Help

If you encounter issues not covered here:

1. Read the [README](../README.md) and in-app help
2. Search [existing issues](https://github.com/metahuan/butlerclaw/issues)
3. Ask in [Discussions](https://github.com/metahuan/butlerclaw/discussions)
4. Open a new [issue](https://github.com/metahuan/butlerclaw/issues/new) with your environment and steps to reproduce
