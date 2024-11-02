import os

import dj_database_url


SECRET_KEY = "django-pgactivity"
# Install the tests as an app so that we can make test models
INSTALLED_APPS = [
    "pgactivity",
    "pgactivity.tests",
]

# Database url comes from the DATABASE_URL env var
DATABASES = {"default": dj_database_url.config()}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

USE_TZ = False
