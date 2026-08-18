from .base import *  # noqa: F401, F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

LOGGING["formatters"]["json"] = {  # noqa: F405
    "format": (
        '{{"timestamp": "{asctime}", "level": "{levelname}", '
        '"logger": "{name}", "message": "{message}"}}'
    ),
    "style": "{",
}
LOGGING["handlers"]["console"]["formatter"] = "json"  # noqa: F405
