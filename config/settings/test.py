from .base import *  # noqa: F401, F403

DEBUG = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# استفاده از SQLite برای تست‌های سریع و ایزوله
# طبق ZRV-BOOT-001 بخش ۴۷، تست‌ها باید بدون وابستگی به PostgreSQL اجرا شوند
DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
