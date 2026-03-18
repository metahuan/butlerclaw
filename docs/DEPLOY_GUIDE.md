# Butlerclaw Deployment Guide

This guide covers the complete process of deploying Butlerclaw as an open-source project.

## Table of Contents

- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Repository Setup](#repository-setup)
- [GitHub Configuration](#github-configuration)
- [CI/CD Setup](#cicd-setup)
- [Release Process](#release-process)
- [Post-Deployment](#post-deployment)

## Pre-Deployment Checklist

### Code Preparation

- [ ] All code is committed and pushed
- [ ] Tests are passing (`pytest tests/`)
- [ ] Code style checks pass (`flake8`)
- [ ] No sensitive data in repository (API keys, passwords)
- [ ] `.gitignore` is properly configured
- [ ] Documentation is complete

### Files Checklist

Required files for open source:

```
✅ LICENSE (MIT)
✅ README.md (English + Chinese)
✅ CONTRIBUTING.md
✅ CODE_OF_CONDUCT.md
✅ SECURITY.md
✅ CHANGELOG.md
✅ .gitignore
✅ requirements.txt
✅ requirements-dev.txt
✅ requirements-build.txt
```

### GitHub Configuration Files

```
✅ .github/
   ├── workflows/
   │   ├── ci.yml
   │   ├── release.yml
   │   └── codeql.yml
   ├── ISSUE_TEMPLATE/
   │   ├── bug_report.md
   │   ├── feature_request.md
   │   ├── documentation.md
   │   └── config.yml
   └── pull_request_template.md
```

### Documentation

```
✅ docs/
   ├── INSTALLATION.md
   ├── USER_MANUAL.md
   ├── API.md
   └── ARCHITECTURE.md
```

### Scripts

```
✅ scripts/
   ├── release.py
   ├── build.py
   ├── version.py
   ├── setup.sh
   └── setup.bat
```

## Repository Setup

### 1. Create GitHub Repository

1. Go to https://github.com/new
2. Enter repository name: `butlerclaw`
3. Add description: "Cross-platform desktop assistant for managing OpenClaw installations"
4. Choose visibility: Public
5. Do NOT initialize with README (we have our own)
6. Click "Create repository"

### 2. Push Existing Code

```bash
# Add remote
git remote add origin https://github.com/yourusername/butlerclaw.git

# Push to main branch
git branch -M main
git push -u origin main

# Push tags
git push origin --tags
```

### 3. Verify Repository

- [ ] All files are uploaded
- [ ] README renders correctly
- [ ] License is detected by GitHub
- [ ] No sensitive files in repository

## GitHub Configuration

### 1. Repository Settings

Navigate to Settings → General:

- **Features:**
  - [ ] Wikis (optional)
  - [x] Issues
  - [x] Discussions
  - [x] Projects
  - [x] Sponsorships (if applicable)

- **Pull Requests:**
  - [x] Allow merge commits
  - [x] Allow squash merging
  - [x] Allow rebase merging
  - [x] Automatically delete head branches

- **Archives:**
  - [x] Include Git LFS objects

### 2. Branch Protection

Navigate to Settings → Branches:

Add rule for `main`:
- [x] Require pull request reviews before merging
  - [x] Dismiss stale PR approvals
  - [x] Require review from CODEOWNERS
- [x] Require status checks to pass
  - [x] Require branches to be up to date
  - Status checks: `test`, `build`
- [x] Require conversation resolution
- [x] Include administrators

### 3. Secrets Configuration

Navigate to Settings → Secrets and variables → Actions:

Add the following secrets if needed:
- `CODECOV_TOKEN` - For code coverage reporting
- `PYPI_API_TOKEN` - If publishing to PyPI

### 4. Enable GitHub Pages (Optional)

Navigate to Settings → Pages:
- Source: Deploy from a branch
- Branch: `gh-pages` /root (or GitHub Actions)

## CI/CD Setup

### GitHub Actions Workflows

The following workflows are configured:

#### CI Workflow (`.github/workflows/ci.yml`)

Runs on every push and PR:
- Tests on Python 3.8-3.12
- Tests on Windows, macOS, Linux
- Code style checks (flake8)
- Type checking (mypy)
- Coverage reporting

#### Release Workflow (`.github/workflows/release.yml`)

Runs on version tags (`v*`):
- Creates GitHub Release
- Builds executables for all platforms
- Uploads release assets
- Generates release notes

#### CodeQL Workflow (`.github/workflows/codeql.yml`)

Runs weekly and on PRs:
- Security analysis
- Code quality checks

### Verifying CI/CD

1. Make a test commit
2. Verify CI workflow runs successfully
3. Check that all tests pass
4. Verify build artifacts are created

## Release Process

### Version Numbering

Butlerclaw follows [Semantic Versioning](https://semver.org/):

- **MAJOR** - Incompatible API changes
- **MINOR** - New functionality (backwards compatible)
- **PATCH** - Bug fixes (backwards compatible)

### Creating a Release

#### Method 1: Using Release Script

```bash
# Bump patch version (2.0.0 -> 2.0.1)
python scripts/release.py patch

# Bump minor version (2.0.0 -> 2.1.0)
python scripts/release.py minor

# Bump major version (2.0.0 -> 3.0.0)
python scripts/release.py major
```

#### Method 2: Manual Release

1. Update version in files:
   ```bash
   python scripts/version.py set 2.1.0
   ```

2. Update CHANGELOG.md

3. Commit and tag:
   ```bash
   git add -A
   git commit -m "Release version 2.1.0"
   git tag -a v2.1.0 -m "Release version 2.1.0"
   git push origin main
   git push origin v2.1.0
   ```

4. GitHub Actions will automatically:
   - Build executables
   - Create GitHub Release
   - Upload assets

### Release Checklist

- [ ] Version updated in all files
- [ ] CHANGELOG.md updated
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Git tag created
- [ ] GitHub Release created
- [ ] Release assets uploaded
- [ ] Release notes written

## Post-Deployment

### Announcements

After release, announce on:
- [ ] GitHub Discussions
- [ ] Twitter/X
- [ ] Reddit (r/OpenClaw, r/Python)
- [ ] Discord/Slack communities
- [ ] Personal blog (if applicable)

### Monitoring

Monitor after release:
- [ ] GitHub Issues for bug reports
- [ ] GitHub Discussions for questions
- [ ] Download statistics
- [ ] Crash reports

### Maintenance

Regular maintenance tasks:
- [ ] Review and merge PRs
- [ ] Respond to issues
- [ ] Update dependencies
- [ ] Security updates
- [ ] Documentation improvements

## Quick Reference

### Common Commands

```bash
# Run tests
pytest tests/ -v

# Build locally
python scripts/build.py all --package

# Create release
python scripts/release.py patch

# Update version
python scripts/version.py bump minor
```

### Directory Structure

```
butlerclaw/
├── .github/              # GitHub configuration
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── tests/                # Test files
├── diagnose/             # Diagnostic modules
├── security/             # Security modules
├── skills/               # Built-in skills
├── ui/                   # UI components
├── web/                  # Web interface
├── openclaw_assistant.py # Main entry point
├── requirements.txt      # Dependencies
├── setup.py             # Package setup
├── LICENSE              # MIT License
├── README.md            # Project readme
├── CHANGELOG.md         # Version history
├── CONTRIBUTING.md      # Contribution guide
├── CODE_OF_CONDUCT.md   # Community guidelines
└── SECURITY.md          # Security policy
```

### Support Resources

- **Issues:** https://github.com/yourusername/butlerclaw/issues
- **Discussions:** https://github.com/yourusername/butlerclaw/discussions
- **Documentation:** https://github.com/yourusername/butlerclaw/tree/main/docs
- **Security:** security@butlerclaw.dev

## Troubleshooting

### CI/CD Issues

**Tests failing:**
- Check test logs in GitHub Actions
- Run tests locally: `pytest tests/ -v`
- Check for platform-specific issues

**Build failures:**
- Verify PyInstaller spec file
- Check for missing dependencies
- Review build logs

### Release Issues

**Tag not triggering release:**
- Ensure tag format is `v*` (e.g., `v2.1.0`)
- Check Actions permissions in repository settings

**Assets not uploading:**
- Verify `GITHUB_TOKEN` permissions
- Check artifact paths in workflow

---

## Summary

Butlerclaw is now ready for open-source deployment with:

✅ Complete documentation
✅ CI/CD pipelines
✅ Automated releases
✅ Issue/PR templates
✅ Security policies
✅ Contribution guidelines

The project follows best practices for open-source Python projects and is ready for community contributions.
