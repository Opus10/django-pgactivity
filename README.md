# django-pgactivity

`django-pgactivity` makes it easy to view, filter, and kill active Postgres queries.

Some of the features at a glance:

* The `PGActivity` proxy model and `pgactivity` management command for querying and filtering the [Postgres pg_stat_activity view](https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW).
* `pgactivity.context` and `pgactivity.middleware.ActivityMiddleware` for annotating queries with application metadata, such as the request URL.
* `pgactivity.cancel` and `pgactivity.terminate` for canceling and terminating queries. The `PGActivity` model manager also has these methods.
* `pgactivity.timeout` for dynamically setting the statement timeout.

## Quick Start

### Basic Command Usage

Use `python manage.py pgactivity` to view and filter active queries. Output looks like the following:

    39225 | 0:01:32 | IDLE_IN_TRANSACTION | None | lock auth_user in access exclusiv
    39299 | 0:00:15 | ACTIVE | None | SELECT "auth_user"."id", "auth_user"."password
    39315 | 0:00:00 | ACTIVE | None | WITH _pgactivity_activity_cte AS ( SELECT pid

The default output attributes are:

1. The process ID of the connection.
2. The duration of the query.
3. The state of the query (see the [Postgres docs](https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW) for values).
4. Attached context using `pgactivity.context`.
5. The query SQL.

Apply filters with `-f` (or `--filter`). Here we query for all active queries that have a duration longer than a minute:

    python manage.py pgactivity -f state=ACTIVE -f 'duration__gt=1 minute'

Cancel or terminate activity with `--cancel` or `--terminate`. Here we terminate a query based on the process ID:

    python manage.py pgactivity 39225 --terminate

### Attaching Context

You can attach context to queries to better understand where they originate using `pgactivity.context` or by adding `pgactivity.middleware.ActivityMiddleware` to `settings.MIDDLEWARE`. Underneath the hood, a comment is added to the SQL statement and surfaced in `django-pgactivity`.

When using the middleware, the `url` of the request and the `method` of the request are automatically added. Here's what the output looks like when using the `pgactivity` command:

    39299 | 0:00:15 | ACTIVE | {"url": "/admin/", "method": "GET"} | SELECT "auth_use

### Proxy Model

Use the `pgactivity.models.PGActivity` proxy model to query the [Postgres pg_stat_activity view](https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW). The model contains most of the fields from the view, and the `cancel` and `terminate` methods can be applied to the queryset.

## Setting the Statement Timeout

Dynamically set the SQL statement timeout of code using `pgactivity.timeout``:

```python
import pgactivity

@pgactivity.timeout(0.5)
def my_operation():
    # Any queries in this operation that take over 500 milliseconds will throw
    # django.db.utils.OperationalError.
```

## Compatibility

`django-pgactivity` is compatible with Python 3.9 - 3.13, Django 4.2 - 5.1, Psycopg 2 - 3, and Postgres 13 - 17.

## Documentation

[View the django-pgactivity docs here](https://django-pgactivity.readthedocs.io) to learn more about:

* The proxy models and custom queryset methods.
* Attaching application context to queries.
* Using and configuring the management command.
* Setting dynamic statement timeouts.

## Installation

Install `django-pgactivity` with:

    pip3 install django-pgactivity
After this, add `pgactivity` to the `INSTALLED_APPS` setting of your Django project.

## Contributing Guide

For information on setting up django-pgactivity for development and contributing changes, view [CONTRIBUTING.md](CONTRIBUTING.md).

## Creators

- [Wes Kendall](https://github.com/wesleykendall)
- [Paul Gilmartin](https://github.com/PaulGilmartin)
