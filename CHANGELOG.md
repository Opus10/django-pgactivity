# Changelog

## 1.4.0 (2023-11-26)

### Feature

  - Django 5.0 compatibility [Wesley Kendall, 12efd20]

    Support and test against Django 5 with psycopg2 and psycopg3.

## 1.3.1 (2023-10-09)

### Trivial

  - Added Opus10 branding to docs [Wesley Kendall, 877178b]

## 1.3.0 (2023-10-08)

### Feature

  - Add Python 3.12 support and use Mkdocs for documentation [Wesley Kendall, ec98a78]

    Python 3.12 and Postgres 16 are supported now, along with having revamped docs using Mkdocs and the Material theme.

    Python 3.7 support was dropped.

## 1.2.0 (2023-06-08)

### Feature

  - Added Python 3.11, Django 4.2, and Psycopg 3 support [Wesley Kendall, 72af215]

    Adds Python 3.11, Django 4.2, and Psycopg 3 support along with tests for multiple Postgres versions. Drops support for Django 2.2.

## 1.1.1 (2022-10-25)

### Trivial

  - Use ``None`` to reset ``pgactivity.timeout``. [Wesley Kendall, fcabcb7]

## 1.1.0 (2022-10-24)

### Feature

  - Simplify management command and nest ``pgactivity.timeout``. [Wesley Kendall, b7d359d]

    The ``pgactivity`` command has been turned into a single management command that can list and kill
    queries rather than having mulitple subcommands.

    The ``pgactivity.timeout`` context manager can now be nested too.

## 1.0.0 (2022-10-18)

### Api-Break

  - Initial release of ``django-pgactivity`` [Wesley Kendall, 593bda7]

    ``django-pgactivity`` makes it easy to view, filter, and kill
    Postgres queries. It comes with the following functionality:

    * The ``PGActivity`` proxy model and ``pgactivity`` management command
      for querying and filtering the ``pg_stats_activity`` table.
    * ``pgactivity.context`` and ``pgactivity.middleware.ActivityMiddleware``
      for annotating queries with application metadata, such as the request URL.
    * ``pgactivity.cancel`` and ``pgactivity.terminate`` for cancelling
      and terminating queries. The ``PGActivity`` model manager also has
      these methods.
    * ``pgactivity.timeout`` for dynamically setting the statement timeout.
