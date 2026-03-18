# User Manual

Complete guide to using Butlerclaw effectively.

## Table of Contents

- [Getting Started](#getting-started)
- [Main Interface](#main-interface)
- [Installation Management](#installation-management)
- [Skill Management](#skill-management)
- [Version Management](#version-management)
- [Diagnostic Tools](#diagnostic-tools)
- [Settings](#settings)
- [Tips and Tricks](#tips-and-tricks)

## Getting Started

### Launching Butlerclaw

- **Windows:** Double-click `Butlerclaw.exe` or run from Start Menu
- **macOS:** Open from Applications folder
- **Linux:** Run `butlerclaw` from terminal or applications menu

### Initial Setup

1. **Welcome Screen** - You'll see the main interface with several tabs
2. **First Installation** - Click "Start Installation" to set up OpenClaw
3. **Model Configuration** - Choose your preferred AI model and enter API key
4. **Ready to Use** - Once configured, you can start using OpenClaw

## Main Interface

The Butlerclaw interface is organized into tabs:

### Sidebar Navigation

| Icon | Tab | Description |
|------|-----|-------------|
| 📦 | Install | Manage OpenClaw installation |
| 🧩 | Skills | Browse and manage skills |
| 🔄 | Version | Check and install updates |
| 🔧 | Diagnose | System diagnostics |
| ⚙️ | Settings | Application settings |

### Common UI Elements

- **Status Bar** - Shows current operation status and version info
- **Log Panel** - Displays operation logs and messages
- **Progress Bar** - Shows progress of long-running operations

## Installation Management

### Running the Installation Wizard

1. Navigate to the **Install** tab
2. Click "Run Installation Wizard"
3. The wizard will:
   - Check for Node.js installation
   - Download and install Node.js if needed
   - Install OpenClaw CLI via npm
   - Configure your preferred model

### Configuration Only

If you already have OpenClaw installed but want to change settings:

1. Click "Configure Model Only"
2. Select your model category (Domestic/International)
3. Choose specific model
4. Enter your API key
5. Click "Save Configuration"

### Testing Connection

After configuration, click "Test Connection" to verify:
- OpenClaw CLI is accessible
- API key is valid
- Model is responding

## Skill Management

### Browsing Skills

1. Navigate to the **Skills** tab
2. Use the search bar to find specific skills
3. Filter by category using the dropdown:
   - All
   - Tools
   - Development
   - Productivity
   - Media
   - Other

### Installing Skills

1. Find the skill you want to install
2. Click the "Install" button
3. Wait for installation to complete
4. The skill will be available in OpenClaw

### Updating Skills

1. Skills with available updates show an "Update" button
2. Click "Update" to get the latest version
3. Or click "Update All" to update all skills at once

### Uninstalling Skills

1. Find the installed skill
2. Click the "Uninstall" button
3. Confirm the uninstallation

### Skill Details

Click on a skill to view:
- Description and features
- Version information
- Author and source
- Documentation link

## Version Management

### Checking for Updates

1. Navigate to the **Version** tab
2. Current and latest versions are displayed
3. Click "Check for Updates" to refresh

### Updating Butlerclaw

If an update is available:
1. Click "Download Update"
2. Wait for download to complete
3. The application will restart automatically

### Viewing Changelog

Click "View Changelog" to see what's new in the latest version.

## Diagnostic Tools

### Running Diagnostics

1. Navigate to the **Diagnose** tab
2. Click "Run Full Diagnostics"
3. The tool will check:
   - Python installation
   - Node.js installation
   - OpenClaw CLI status
   - Configuration files
   - Network connectivity
   - API key validity

### Understanding Results

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ Pass | Everything is working | None needed |
| ⚠️ Warning | Non-critical issue | Review recommendation |
| ❌ Error | Critical problem | Follow fix instructions |

### Exporting Reports

1. Run diagnostics
2. Click "Export Report"
3. Choose save location
4. Share the report when seeking support

### Common Fixes

The diagnostic tool can automatically fix some issues:
- Repair configuration files
- Reset API keys
- Clear cache

## Settings

### General Settings

- **Language** - Select interface language
- **Theme** - Choose light or dark theme
- **Auto-check Updates** - Enable/disable automatic update checks
- **Start Minimized** - Start Butlerclaw minimized to system tray

### Advanced Settings

- **Log Level** - Set verbosity of logs (Debug, Info, Warning, Error)
- **Cache Directory** - Change location of cache files
- **Network Timeout** - Adjust timeout for network operations
- **Proxy Settings** - Configure HTTP proxy if needed

### Backup and Restore

**Backup Configuration:**
1. Go to Settings → Backup
2. Click "Export Configuration"
3. Save the backup file

**Restore Configuration:**
1. Go to Settings → Backup
2. Click "Import Configuration"
3. Select your backup file

## Tips and Tricks

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + 1` | Switch to Install tab |
| `Ctrl + 2` | Switch to Skills tab |
| `Ctrl + 3` | Switch to Version tab |
| `Ctrl + 4` | Switch to Diagnose tab |
| `Ctrl + 5` | Switch to Settings tab |
| `Ctrl + R` | Refresh current view |
| `Ctrl + Q` | Quit application |
| `F1` | Open help |

### Performance Tips

1. **Clear Cache Regularly** - Old cache files can slow down the app
2. **Disable Unused Skills** - Reduces OpenClaw startup time
3. **Use Wired Connection** - For faster downloads during installation

### Security Best Practices

1. **Never share your API keys**
2. **Regular backups** - Export configuration periodically
3. **Keep updated** - Install security updates promptly
4. **Use strong passwords** - Protect your user account

### Troubleshooting Mode

If Butlerclaw won't start normally:

1. Hold `Shift` while starting to enter Safe Mode
2. Run diagnostics
3. Reset configuration if needed

## Getting Help

### In-App Help

- Click the `?` button in any tab for context-sensitive help
- View tooltips by hovering over UI elements

### Online Resources

- 📖 [Full Documentation](https://github.com/yourusername/butlerclaw/tree/main/docs)
- 💬 [Community Discussions](https://github.com/yourusername/butlerclaw/discussions)
- 🐛 [Issue Tracker](https://github.com/yourusername/butlerclaw/issues)

### Reporting Issues

When reporting problems:
1. Run diagnostics and export the report
2. Note your operating system and version
3. Describe steps to reproduce the issue
4. Include any error messages
