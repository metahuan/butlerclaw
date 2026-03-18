# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.0.x   | :x:                |

## Reporting a Vulnerability

We take the security of Butlerclaw seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Please do not report security vulnerabilities through public GitHub issues.

Instead, please report them via email to **security@butlerclaw.dev** (or create a private security advisory on GitHub if enabled).

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information in your report:

- **Type of issue** (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- **Full paths of source file(s) related to the manifestation of the issue**
- **The location of the affected source code** (tag/branch/commit or direct URL)
- **Any special configuration required to reproduce the issue**
- **Step-by-step instructions to reproduce the issue**
- **Proof-of-concept or exploit code** (if possible)
- **Impact of the issue**, including how an attacker might exploit it

## Security Best Practices

### For Users

1. **Keep your software updated** - Always use the latest version of Butlerclaw
2. **Protect your API keys** - Never share your API keys or commit them to version control
3. **Use environment variables** - Store sensitive configuration in environment variables
4. **Verify downloads** - When downloading Butlerclaw, verify the source is legitimate
5. **Report suspicious behavior** - If you notice unusual activity, report it immediately

### For Developers

1. **Never hardcode secrets** - Use environment variables or secure key management
2. **Validate all inputs** - Sanitize user inputs to prevent injection attacks
3. **Use parameterized queries** - When interacting with databases
4. **Keep dependencies updated** - Regularly update dependencies to patch security issues
5. **Follow secure coding practices** - Refer to our secure coding guidelines in `docs/SECURITY_GUIDE.md`

## Security Features

Butlerclaw implements several security features:

- **API Key Encryption** - API keys are encrypted at rest
- **Secure Configuration Storage** - Configuration files use appropriate permissions
- **Input Validation** - All user inputs are validated and sanitized
- **Secure Communication** - HTTPS is used for all network communications
- **Dependency Scanning** - Regular scanning of dependencies for known vulnerabilities

## Known Security Considerations

### API Key Storage

Butlerclaw stores API keys in the user's home directory (`~/.openclaw/`). While we implement encryption, users should:
- Ensure their user account is protected with a strong password
- Use file system permissions to restrict access to configuration files
- Consider using a password manager for additional security

### Network Communication

When downloading Node.js or OpenClaw packages:
- All downloads use HTTPS
- Checksums are verified when available
- Downloads are from official sources (nodejs.org, npm registry)

## Security Update Process

1. Security issues are triaged within 48 hours
2. Critical vulnerabilities are patched as soon as possible
3. Security updates are released as patch versions (e.g., 2.0.1)
4. Users are notified through:
   - GitHub Security Advisories
   - Release notes
   - In-app notifications (when applicable)

## Acknowledgments

We would like to thank the following security researchers who have responsibly disclosed vulnerabilities:

*This list will be updated as contributions are received.*

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python-security.readthedocs.io/)
- [Node.js Security Best Practices](https://nodejs.org/en/docs/guides/security/)
