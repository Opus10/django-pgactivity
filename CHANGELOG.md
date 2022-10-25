# Changelog
## 1.1.1 (2022-10-24)
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

