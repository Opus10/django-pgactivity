# Changelog
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

