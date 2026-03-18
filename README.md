# Butlerclaw

[![CI](https://github.com/<your-github-username>/butlerclaw/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-github-username>/butlerclaw/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> 🎯 **Butlerclaw** - Your intelligent assistant for managing OpenClaw installations and configurations.

[English](#english) | [中文](#中文)

---

## English

### Overview

Butlerclaw is a cross-platform desktop application that simplifies the installation, configuration, and management of OpenClaw. Built with Python and tkinter, it provides an intuitive graphical interface for:

- **One-click Installation** - Automatic Node.js and OpenClaw setup
- **Skill Management** - Browse, install, and manage OpenClaw skills
- **Version Control** - Check for updates and manage different versions
- **Diagnostics** - Comprehensive system diagnostics and troubleshooting
- **Multi-platform Support** - Works on Windows, macOS, and Linux

### Features

- 🚀 **Easy Installation** - Automated setup with progress tracking
- 🎨 **Modern UI** - Clean, intuitive interface with dark/light themes
- 🔧 **Skill Marketplace** - Browse and install skills from ClawHub
- 🔒 **Secure** - Encrypted API key storage and secure configuration
- 🌐 **Multi-language** - Support for multiple languages (in development)
- 📊 **Diagnostics** - Built-in system diagnostics and log export

### Installation

#### Option 1: Pre-built Executable (Recommended)

Download the latest release for your platform:

- **Windows**: `Butlerclaw-Windows.exe`
- **macOS**: `Butlerclaw-macOS.dmg`
- **Linux**: `Butlerclaw-Linux.tar.gz`

#### Option 2: From Source

```bash
# Clone the repository
git clone https://github.com/<your-github-username>/butlerclaw.git
cd butlerclaw

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python openclaw_assistant.py
```

### Requirements

- Python 3.8 or higher
- tkinter (usually included with Python)
- Node.js 18+ (will be installed automatically if not present)

### Quick Start

1. Launch Butlerclaw
2. Click "Start Installation" to install Node.js and OpenClaw
3. Configure your preferred AI model and API key
4. Start using OpenClaw!

### Supported Models

#### Domestic (China)
- **Kimi K2.5** (Moonshot) - Excellent Chinese language support
- **DeepSeek V3** - Strong reasoning capabilities
- **DeepSeek R1** - Advanced reasoning model
- **Qwen 2.5** (Alibaba) - Multilingual capabilities

#### International
- **GPT-4o** (OpenAI) - Best overall capabilities
- **Claude 3.5 Sonnet** (Anthropic) - Excellent for coding
- **Gemini 2.0 Flash** (Google) - Strong multimodal capabilities

### Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [User Manual](docs/USER_MANUAL.md)
- [API Documentation](docs/API.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

### Development

```bash
# Setup development environment
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Build executable
# Windows:
python -m PyInstaller OpenClaw安装助手.spec
# macOS:
./build_macos.sh
# Linux:
./build_linux.sh
```

### Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 中文

### 概述

Butlerclaw 是一个跨平台桌面应用程序，旨在简化 OpenClaw 的安装、配置和管理。基于 Python 和 tkinter 构建，提供直观的图形界面：

- **一键安装** - 自动安装 Node.js 和 OpenClaw
- **技能管理** - 浏览、安装和管理 OpenClaw 技能
- **版本控制** - 检查更新和管理不同版本
- **诊断工具** - 全面的系统诊断和故障排除
- **多平台支持** - 支持 Windows、macOS 和 Linux

### 功能特点

- 🚀 **简易安装** - 自动化设置，带进度跟踪
- 🎨 **现代界面** - 简洁直观的界面，支持深色/浅色主题
- 🔧 **技能市场** - 从 ClawHub 浏览和安装技能
- 🔒 **安全可靠** - API 密钥加密存储和安全配置
- 🌐 **多语言** - 支持多种语言（开发中）
- 📊 **诊断工具** - 内置系统诊断和日志导出

### 安装方法

#### 方式一：预构建可执行文件（推荐）

下载适合您平台的最新版本：

- **Windows**: `Butlerclaw-Windows.exe`
- **macOS**: `Butlerclaw-macOS.dmg`
- **Linux**: `Butlerclaw-Linux.tar.gz`

#### 方式二：从源码安装

```bash
# 克隆仓库
git clone https://github.com/<your-github-username>/butlerclaw.git
cd butlerclaw

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行应用程序
python openclaw_assistant.py
```

### 系统要求

- Python 3.8 或更高版本
- tkinter（通常随 Python 一起安装）
- Node.js 18+（如未安装将自动安装）

### 快速开始

1. 启动 Butlerclaw
2. 点击"开始安装"安装 Node.js 和 OpenClaw
3. 配置您偏好的 AI 模型和 API 密钥
4. 开始使用 OpenClaw！

### 支持的模型

#### 国产模型
- **Kimi K2.5** (Moonshot) - 优秀的中文支持
- **DeepSeek V3** - 强大的推理能力
- **DeepSeek R1** - 高级推理模型
- **通义千问 2.5** (阿里) - 多语言能力

#### 国际模型
- **GPT-4o** (OpenAI) - 最佳综合能力
- **Claude 3.5 Sonnet** (Anthropic) - 编程能力出色
- **Gemini 2.0 Flash** (Google) - 强大的多模态能力

### 文档

- [安装指南](docs/INSTALLATION.md)
- [用户手册](docs/USER_MANUAL.md)
- [API 文档](docs/API.md)
- [架构说明](docs/ARCHITECTURE.md)
- [贡献指南](CONTRIBUTING.md)

### 开发

```bash
# 设置开发环境
pip install -r requirements-dev.txt

# 运行测试
pytest tests/ -v

# 构建可执行文件
# Windows:
python -m PyInstaller OpenClaw安装助手.spec
# macOS:
./build_macos.sh
# Linux:
./build_linux.sh
```

### 贡献

我们欢迎贡献！详情请参阅我们的[贡献指南](CONTRIBUTING.md)。

### 开源协议

本项目采用 MIT 协议开源 - 详见 [LICENSE](LICENSE) 文件。

---

## Acknowledgments

- [OpenClaw](https://github.com/openclaw) - The core framework that Butlerclaw manages
- All our [contributors](https://github.com/<your-github-username>/butlerclaw/graphs/contributors) who make this project possible

## Support

- 💬 [GitHub Discussions](https://github.com/<your-github-username>/butlerclaw/discussions)
- 🐛 [Issue Tracker](https://github.com/<your-github-username>/butlerclaw/issues)
- 📧 Email: <your-support-email>
