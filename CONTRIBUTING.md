# Contributing to Butlerclaw

First off, thank you for considering contributing to Butlerclaw! It's people like you that make Butlerclaw such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our commitment to:
- Being respectful and inclusive
- Welcoming newcomers
- Focusing on constructive feedback
- Prioritizing user experience

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to see if the problem has already been reported. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed and what behavior you expected**
- **Include screenshots if applicable**
- **Specify your environment:**
  - Operating system and version
  - Python version
  - Node.js version (if applicable)
  - Butlerclaw version

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the enhancement**
- **Explain why this enhancement would be useful**

### Pull Requests

1. Fork the repository
2. Create a new branch from `main` for your feature or bug fix
3. Make your changes
4. Run the tests locally
5. Update documentation as needed
6. Submit a pull request

#### Pull Request Process

1. Ensure your code follows the existing code style
2. Update the README.md or relevant documentation with details of changes if applicable
3. Add tests for any new functionality
4. Ensure all tests pass
5. Your PR will be reviewed by maintainers who may request changes

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Node.js 18+ (for testing OpenClaw integration)
- Git

### Setting Up Your Development Environment

```bash
# Clone your fork
git clone https://github.com/yourusername/butlerclaw.git
cd butlerclaw

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run the application in development mode
python openclaw_assistant.py
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_installer.py

# Run with verbose output
python -m pytest tests/ -v
```

## Style Guidelines

### Python Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use 4 spaces for indentation
- Maximum line length of 100 characters
- Use descriptive variable names
- Add docstrings to functions and classes

Example:
```python
def install_package(package_name: str, version: str = None) -> bool:
    """
    Install a package using npm.
    
    Args:
        package_name: Name of the package to install
        version: Specific version to install (optional)
        
    Returns:
        True if installation succeeded, False otherwise
    """
    # Implementation here
    pass
```

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

Example:
```
Add skill search functionality

- Implement fuzzy search for skill names
- Add keyboard shortcuts for quick access
- Fixes #123
```

## Project Structure

```
butlerclaw/
├── diagnose/          # Diagnostic tools
├── security/          # Security-related modules
├── skills/            # Skill management
├── tests/             # Test files
├── ui/                # UI components
├── web/               # Web interface
├── web-components/    # Reusable web components
├── docs/              # Documentation
└── scripts/           # Build and utility scripts
```

## Testing Guidelines

- Write tests for new features
- Ensure existing tests pass before submitting PR
- Aim for high test coverage on critical paths
- Use mocking for external dependencies (network, file system)

## Documentation

- Update README.md if you change functionality
- Add docstrings to new functions and classes
- Update CHANGELOG.md for notable changes
- Consider adding examples for complex features

## Questions?

Feel free to open an issue with your question or contact the maintainers.

Thank you for contributing! 🎉
