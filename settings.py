import os

import dj_database_url


SECRET_KEY = "django-pgactivity"
# Install the tests as an app so that we can make test models
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "pgactivity",
    "pgactivity.tests",
]

# Database url comes from the DATABASE_URL env var
DATABASES = {"default": dj_database_url.config()}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "pgactivity.middleware.ActivityMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Options for testing the admin locally and in tests
ALLOWED_HOSTS = []
DEBUG = True
ROOT_URLCONF = "pgactivity.tests.urls"
STATIC_URL = "/static/"

SHELL_PLUS = "ipython"

PGACTIVITY_CONFIGS = {
    "long-running": {
        "limit": 1,
        "filters": ["duration__gt=1 minute"],
    }
}
PGACTIVITY_LIMIT = 25

USE_TZ = False
