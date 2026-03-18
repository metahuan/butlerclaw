# Architecture Overview

This document provides a high-level overview of Butlerclaw's architecture and design principles.

## Table of Contents

- [System Architecture](#system-architecture)
- [Design Principles](#design-principles)
- [Component Overview](#component-overview)
- [Data Flow](#data-flow)
- [Security Architecture](#security-architecture)
- [Extension Points](#extension-points)

## System Architecture

Butlerclaw follows a layered architecture pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface Layer                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Install │ │  Skills  │ │ Version  │ │ Diagnose │       │
│  │  Panel   │ │  Panel   │ │  Panel   │ │  Panel   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │   Installer  │ │    Skill     │ │   Version    │        │
│  │   Manager    │ │   Manager    │ │   Manager    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Integration Layer                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ OpenClaw │ │ ClawHub  │ │  Node.js │ │  System  │       │
│  │   CLI    │ │   API    │ │Installer │ │   Info   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Design Principles

### 1. Cross-Platform Compatibility

Butlerclaw is designed to work seamlessly across Windows, macOS, and Linux:

- **Platform Abstraction**: Platform-specific code is isolated in dedicated modules
- **Consistent Interface**: Same user experience across all platforms
- **Adaptive Behavior**: Automatically adapts to platform conventions

### 2. Modular Design

Each feature is implemented as an independent module:

- **Separation of Concerns**: UI, business logic, and data access are separated
- **Plugin Architecture**: Skills can be added/removed without core changes
- **Testability**: Modules can be tested independently

### 3. User-Centric Design

Focus on simplicity and ease of use:

- **Progressive Disclosure**: Simple by default, powerful when needed
- **Visual Feedback**: Clear progress indicators and status messages
- **Error Recovery**: Helpful error messages with suggested fixes

### 4. Security First

Security is built into every layer:

- **Encryption**: API keys are encrypted at rest
- **Least Privilege**: Minimal permissions required
- **Secure Defaults**: Secure configuration out of the box

## Component Overview

### UI Layer

#### Main Application (`openclaw_assistant.py`)

The main entry point that coordinates all UI components:

- **Window Management**: Creates and manages the main application window
- **Navigation**: Handles tab switching and panel management
- **Event Coordination**: Routes events between panels and backend

#### Panels

Each panel is a self-contained UI component:

| Panel | Purpose | Key Features |
|-------|---------|--------------|
| InstallPanel | Installation management | Wizard interface, progress tracking |
| SkillsPanel | Skill management | Search, filter, install/uninstall |
| VersionPanel | Version control | Update checking, changelog viewing |
| DiagnosePanel | System diagnostics | Health checks, report export |
| SettingsPanel | Configuration | Preferences, backup/restore |

### Business Logic Layer

#### Installation Manager

Handles the installation process:

- check_prerequisites()
- download_dependencies()
- install_nodejs()
- install_openclaw()
- configure_environment()

#### Skill Manager

Manages the skill lifecycle:

- fetch_catalog()
- install_skill(skill_id)
- uninstall_skill(skill_id)
- update_skill(skill_id)
- get_skill_status(skill_id)

#### Version Manager

Handles version checking and updates:

- check_for_updates()
- download_update()
- apply_update()
- rollback_update()

### Integration Layer

#### OpenClaw CLI Integration

Communicates with the OpenClaw command-line interface:

- **Command Execution**: Runs OpenClaw commands
- **Output Parsing**: Parses command output
- **Error Handling**: Handles CLI errors gracefully

#### ClawHub API

Interfaces with the ClawHub skill marketplace:

- **Authentication**: OAuth2-based authentication
- **Catalog Fetching**: Retrieves skill catalog
- **Download Management**: Handles skill downloads

#### Node.js Installer

Platform-specific Node.js installation:

- **Version Detection**: Checks installed Node.js version
- **Download**: Fetches appropriate Node.js distribution
- **Installation**: Installs Node.js system-wide or user-local

## Data Flow

### Installation Flow

```
User clicks "Install"
       │
       ▼
┌──────────────┐
│  UI Layer    │ ──► Shows progress dialog
└──────────────┘
       │
       ▼
┌──────────────┐
│ Business     │ ──► InstallationManager.run()
│ Logic        │
└──────────────┘
       │
       ▼
┌──────────────┐
│ Integration  │ ──► Download Node.js
│ Layer        │ ──► Install OpenClaw
└──────────────┘
       │
       ▼
┌──────────────┐
│  UI Layer    │ ──► Shows completion
└──────────────┘
```

## Security Architecture

### Data Protection

- API keys encrypted using platform-specific key storage
- Configuration files with restricted permissions
- Secure temporary file handling
- Memory clearing for sensitive data

### Communication Security

- HTTPS for all network communications
- Certificate validation
- Secure download verification

## Extension Points

### Adding New Skills

Skills can be added through:
1. ClawHub marketplace
2. Manual installation
3. Custom skill development

### Custom Panels

New panels can be added by:
1. Extending BasePanel class
2. Implementing required methods
3. Registering in main application

### Platform Support

New platforms can be supported by:
1. Creating platform-specific installer
2. Implementing platform detection
3. Adding platform-specific utilities
