"""Use SQLite and zero SMS delay for fast tests without external services."""

import os

os.environ.setdefault("DEBUG", "1")
os.environ.setdefault("USE_SQLITE", "1")

from . import settings as base_settings  # noqa: E402
from .settings import *  # noqa: F403,E402,F401

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5
SMS_SIMULATED_DELAY_SECONDS = 0
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

REST_FRAMEWORK = {
    **base_settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        "sms": "100000/hour",
        "verify": "100000/hour",
    },
}

STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
