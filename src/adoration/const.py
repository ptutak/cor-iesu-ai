class DefaultValues:
    """Default configuration values for the adoration application."""

    ASSIGNMENT_LIMIT = 2
    DEFAULT_EMAIL_TIMEOUT = 30
    MAX_COLLECTION_NAME_LENGTH = 100
    DEFAULT_LANGUAGE = "en"


class EmailSettings:
    """Email configuration constants."""

    EMAIL_SUBJECT_PREFIX = "[Adoration] "


class ValidationMessages:
    """Standard validation error messages."""

    REQUIRED_FIELD = "This field is required."
    INVALID_EMAIL = "Enter a valid email address."
    COLLECTION_DISABLED = "This collection is currently disabled."
