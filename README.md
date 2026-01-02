# cor-iesu-ai

Package for managing adoration of Most Holy Sacrament

## Development Setup

### Prerequisites

- Python 3.13+
- Ruby (for MailCatcher)
- Git

### Installation

1. **Install development dependencies:**
   ```bash
   make install-dev
   ```

2. **Set up database:**
   ```bash
   make migrations
   ```

3. **Run development server:**
   ```bash
   make run-dev
   ```

This will automatically:
- Start MailCatcher in the background (SMTP server for testing emails)
- Start the Django development server
- Configure email routing to MailCatcher

### Development URLs

- **Django App**: http://localhost:8000
- **MailCatcher Web Interface**: http://localhost:1080

### Email Testing

When running in development mode, all emails sent by the application are captured by MailCatcher instead of being sent to real email addresses. You can:

1. Trigger email sending through the app (e.g., register for a period)
2. View the captured emails at http://localhost:1080
3. See the full email content, headers, and deletion links

### Useful Commands

```bash
# Start development environment
make run-dev

# Stop MailCatcher
make stop-mailcatcher

# Clean development environment
make clean-dev

# Run code quality checks
make check-hooks

# Create/apply migrations
make migrations
```

### MailCatcher Features

- **Web Interface**: View all captured emails in your browser
- **No Setup**: Automatically installed and configured
- **Safe Testing**: No risk of sending emails to real users during development
- **Full Email Support**: HTML/text emails, attachments, headers

### Code Quality

The project uses:
- **mypy** for type checking
- **black** for code formatting
- **flake8** for linting
- **pre-commit** hooks for automated quality checks

Run `make check-hooks` to verify code quality before committing.
