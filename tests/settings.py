"""
Django test settings for isolated testing environment.

This configuration ensures each test gets its own isolated SQLite database
for maximum test isolation and reliability.
"""

import os
import tempfile
from pathlib import Path

# Import base settings from main project
from coreiesuai.settings import *

# Override database settings for testing
# Use a temporary SQLite database that gets created fresh for each test run
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "OPTIONS": {
            "timeout": 20,
        },
        "TEST": {
            "NAME": ":memory:",
        },
    }
}

# Use dummy email backend for testing to capture emails
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable password validators for test performance
AUTH_PASSWORD_VALIDATORS = []

# Use simple password hasher for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable logging during tests
LOGGING_CONFIG = None
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["console"],
    },
}

# Use simple cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Test-specific security settings
SECRET_KEY = "test-secret-key-for-testing-only-not-for-production-use"
DEBUG = True
ALLOWED_HOSTS = ["*", "testserver", "localhost", "127.0.0.1"]

# Disable CSRF for testing
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Media and static files for testing
MEDIA_ROOT = tempfile.mkdtemp(prefix="test_media_")
STATIC_ROOT = tempfile.mkdtemp(prefix="test_static_")

# Test-specific middleware (remove security middleware that might interfere)
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]


# Disable migrations for faster test runs
class DisableMigrations:
    """
    Disable migrations by making Django think no migrations exist.
    This speeds up test database creation significantly.
    """

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


# Uncomment the line below if you want to disable migrations for faster tests
# MIGRATION_MODULES = DisableMigrations()

# Test runner settings
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Ensure test databases are properly isolated
DATABASE_ROUTERS = []

# Time zone for tests
USE_TZ = True
TIME_ZONE = "UTC"

# Internationalization for tests
USE_I18N = True
USE_L10N = True
LANGUAGE_CODE = "en-us"
