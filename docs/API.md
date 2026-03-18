# API Documentation

This document describes the internal APIs and modules of Butlerclaw for developers.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Modules](#core-modules)
- [Installation Module](#installation-module)
- [Skill Management](#skill-management)
- [Configuration](#configuration)
- [Diagnostics](#diagnostics)
- [Utilities](#utilities)

## Architecture Overview

Butlerclaw follows a modular architecture:

```
butlerclaw/
├── openclaw_assistant.py    # Main application entry point
├── openclaw_installer_*.py  # Platform-specific installers
├── skills_manager.py        # Skill management logic
├── skills_panel_new.py      # Skill UI components
├── hub_auth.py             # Authentication for ClawHub
├── hub_skills_api.py       # ClawHub API client
├── clawhub_api.py          # ClawHub integration
├── diagnose/               # Diagnostic tools
├── security/               # Security utilities
├── skills/                 # Built-in skills
├── ui/                     # UI components
├── web/                    # Web interface
└── web-components/         # Reusable web components
```

## Core Modules

### Main Application (`openclaw_assistant.py`)

The main entry point that initializes the tkinter GUI and coordinates all modules.

```python
class ButlerclawApp:
    """Main application class."""
    
    def __init__(self):
        """Initialize the application."""
        pass
    
    def run(self):
        """Start the main event loop."""
        pass
```

### Base Panel (`BasePanel`)

Base class for all UI panels.

```python
class BasePanel(ttk.Frame):
    """Base class for all panels."""
    
    def __init__(self, parent, app, **kwargs):
        """
        Initialize panel.
        
        Args:
            parent: Parent widget
            app: Reference to main application
        """
        pass
    
    def on_show(self):
        """Called when panel becomes visible."""
        pass
```

## Installation Module

### Platform Installers

#### Windows (`openclaw_installer_v2.py`)

```python
class OpenClawInstaller:
    """Windows installer for OpenClaw."""
    
    def __init__(self, log_callback=None, progress_callback=None):
        """
        Initialize installer.
        
        Args:
            log_callback: Function to call with log messages
            progress_callback: Function to call with progress updates
        """
        pass
    
    def check_nodejs(self):
        """
        Check if Node.js is installed.
        
        Returns:
            tuple: (is_installed, version)
        """
        pass
    
    def install_nodejs(self):
        """
        Download and install Node.js.
        
        Returns:
            bool: True if successful
        """
        pass
    
    def install_openclaw(self):
        """
        Install OpenClaw via npm.
        
        Returns:
            bool: True if successful
        """
        pass
    
    def run_full_installation(self):
        """
        Run complete installation process.
        
        Returns:
            bool: True if all steps succeeded
        """
        pass
```

#### macOS (`openclaw_installer_macos.py`)

Same interface as Windows installer with macOS-specific implementations.

#### Linux (`openclaw_installer_linux.py`)

Same interface with Linux-specific implementations.

## Skill Management

### Skill Manager (`skills_manager.py`)

```python
class SkillManager:
    """Manages OpenClaw skills."""
    
    def __init__(self):
        """Initialize skill manager."""
        pass
    
    def get_installed_skills(self):
        """
        Get list of installed skills.
        
        Returns:
            list: Installed skill dictionaries
        """
        pass
    
    def get_available_skills(self):
        """
        Get list of available skills from ClawHub.
        
        Returns:
            list: Available skill dictionaries
        """
        pass
    
    def install_skill(self, skill_id):
        """
        Install a skill.
        
        Args:
            skill_id: Unique identifier of the skill
            
        Returns:
            bool: True if successful
        """
        pass
    
    def uninstall_skill(self, skill_id):
        """
        Uninstall a skill.
        
        Args:
            skill_id: Unique identifier of the skill
            
        Returns:
            bool: True if successful
        """
        pass
    
    def update_skill(self, skill_id):
        """
        Update a skill to latest version.
        
        Args:
            skill_id: Unique identifier of the skill
            
        Returns:
            bool: True if successful
        """
        pass
```

### Skill Data Structure

```python
{
    "id": "weather",
    "name": "Weather",
    "name_zh": "天气查询",
    "description": "Get current weather and forecasts",
    "description_zh": "获取当前天气和预报",
    "icon": "☔",
    "category": "tool",
    "version": "1.2.0",
    "author": "OpenClaw Team",
    "source": "clawhub",
    "installed": True,
    "update_available": False
}
```

## Configuration

### Configuration Manager

```python
class ConfigManager:
    """Manages application configuration."""
    
    CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")
    
    def __init__(self):
        """Initialize configuration manager."""
        pass
    
    def load(self):
        """
        Load configuration from file.
        
        Returns:
            dict: Configuration dictionary
        """
        pass
    
    def save(self, config):
        """
        Save configuration to file.
        
        Args:
            config: Configuration dictionary
        """
        pass
    
    def get(self, key, default=None):
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        pass
    
    def set(self, key, value):
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        pass
```

### Configuration Schema

```python
{
    "version": "2.0.0",
    "model": {
        "provider": "moonshot",
        "model": "kimi-k2.5",
        "api_key": "encrypted_api_key"
    },
    "ui": {
        "theme": "dark",
        "language": "zh-CN"
    },
    "advanced": {
        "log_level": "info",
        "cache_dir": "~/.openclaw/cache",
        "network_timeout": 30
    }
}
```

## Diagnostics

### Diagnostic Runner

```python
class DiagnosticRunner:
    """Runs system diagnostics."""
    
    def __init__(self):
        """Initialize diagnostic runner."""
        pass
    
    def run_all_checks(self):
        """
        Run all diagnostic checks.
        
        Returns:
            dict: Diagnostic results
        """
        pass
    
    def check_python(self):
        """
        Check Python installation.
        
        Returns:
            dict: Check result
        """
        pass
    
    def check_nodejs(self):
        """
        Check Node.js installation.
        
        Returns:
            dict: Check result
        """
        pass
    
    def check_openclaw(self):
        """
        Check OpenClaw installation.
        
        Returns:
            dict: Check result
        """
        pass
    
    def check_configuration(self):
        """
        Check configuration files.
        
        Returns:
            dict: Check result
        """
        pass
    
    def export_report(self, path):
        """
        Export diagnostic report to file.
        
        Args:
            path: Export file path
        """
        pass
```

### Diagnostic Result Format

```python
{
    "timestamp": "2026-03-18T10:30:00Z",
    "overall_status": "pass",  # pass, warning, error
    "checks": [
        {
            "name": "Python Installation",
            "status": "pass",
            "message": "Python 3.11.4 found",
            "details": {...}
        },
        {
            "name": "Node.js Installation",
            "status": "warning",
            "message": "Node.js not found",
            "details": {...},
            "recommendation": "Run installation wizard"
        }
    ]
}
```

## Utilities

### Logger

```python
class Logger:
    """Application logger."""
    
    def __init__(self, name, level="info"):
        """
        Initialize logger.
        
        Args:
            name: Logger name
            level: Log level (debug, info, warning, error)
        """
        pass
    
    def debug(self, message):
        """Log debug message."""
        pass
    
    def info(self, message):
        """Log info message."""
        pass
    
    def warning(self, message):
        """Log warning message."""
        pass
    
    def error(self, message):
        """Log error message."""
        pass
```

### Platform Detection

```python
def get_platform():
    """
    Get current platform.
    
    Returns:
        str: 'windows', 'macos', or 'linux'
    """
    pass

def get_user_home():
    """
    Get user home directory.
    
    Returns:
        str: Path to user home directory
    """
    pass

def is_admin():
    """
    Check if running with administrator privileges.
    
    Returns:
        bool: True if admin
    """
    pass
```

## Events

### Event System

```python
class EventEmitter:
    """Simple event emitter for inter-module communication."""
    
    def __init__(self):
        """Initialize event emitter."""
        pass
    
    def on(self, event, callback):
        """
        Subscribe to an event.
        
        Args:
            event: Event name
            callback: Function to call when event fires
        """
        pass
    
    def off(self, event, callback):
        """
        Unsubscribe from an event.
        
        Args:
            event: Event name
            callback: Function to remove
        """
        pass
    
    def emit(self, event, *args, **kwargs):
        """
        Emit an event.
        
        Args:
            event: Event name
            *args: Positional arguments for callbacks
            **kwargs: Keyword arguments for callbacks
        """
        pass
```

## Error Handling

### Custom Exceptions

```python
class ButlerclawError(Exception):
    """Base exception for Butlerclaw."""
    pass

class InstallationError(ButlerclawError):
    """Raised when installation fails."""
    pass

class ConfigurationError(ButlerclawError):
    """Raised when configuration is invalid."""
    pass

class NetworkError(ButlerclawError):
    """Raised when network operation fails."""
    pass

class SkillError(ButlerclawError):
    """Raised when skill operation fails."""
    pass
```

## Threading

### Thread Utilities

```python
def run_in_thread(func, *args, **kwargs):
    """
    Run a function in a separate thread.
    
    Args:
        func: Function to run
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Thread: The started thread
    """
    pass

class ThreadSafeQueue:
    """Thread-safe queue for inter-thread communication."""
    pass
```
