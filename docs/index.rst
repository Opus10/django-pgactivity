django-pgactivity
=================

``django-pgactivity`` makes it easy to view, filter, and kill
active Postgres queries.

Some of the features at a glance:

* The `PGActivity` proxy model and ``pgactivity`` management command
  for querying and filtering the `Postgres pg_stat_activity view <https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW>`__.
* `pgactivity.context` and `pgactivity.middleware.ActivityMiddleware`
  for annotating queries with application metadata, such as the request URL.
* `pgactivity.cancel` and `pgactivity.terminate` for canceling
  and terminating queries. The `PGActivity` model manager also has
  these methods.
* `pgactivity.timeout` for dynamically setting the statement timeout.

Quick Start
-----------

Basic Command Usage
~~~~~~~~~~~~~~~~~~~

Use ``python manage.py pgactivity`` to view and filter active queries. Output looks like the following::

    39225 | 0:01:32 | IDLE_IN_TRANSACTION | None | lock auth_user in access exclusiv
    39299 | 0:00:15 | ACTIVE | None | SELECT "auth_user"."id", "auth_user"."password
    39315 | 0:00:00 | ACTIVE | None | WITH _pgactivity_activity_cte AS ( SELECT pid

The default output attributes are:

1. The process ID of the connection.
2. The duration of the query.
3. The state of the query (see the `Postgres docs <https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW>`__ for values).
4. Attached context using `pgactivity.context`.
5. The query SQL.

Apply filters with ``-f`` (or ``--filter``). Here we query for all active queries that have a duration
longer than a minute::

    python manage.py pgactivity -f state=ACTIVE -f 'duration__gt=1 minute'

Cancel or terminate activity with ``--cancel`` or ``--terminate``.
Here we terminate a query based on the process ID::

    python manage.py pgactivity 39225 --terminate

Attaching Context
~~~~~~~~~~~~~~~~~

You can attach context to queries to better understand where they originate
using `pgactivity.context` or by adding `pgactivity.middleware.ActivityMiddleware`
to ``settings.MIDDLEWARE``.
Underneath the hood, a comment is added to the SQL statement and surfaced in
``django-pgactivity``.

When using the middleware, the ``url`` of the request and the ``method`` of
the request are automatically added. Here's what the output looks like
when using the ``pgactivity`` command::

    39299 | 0:00:15 | ACTIVE | {"url": "/admin/", "method": "GET"} | SELECT "auth_use

Proxy Model
~~~~~~~~~~~

Use the `pgactivity.models.PGActivity` proxy model to query
the `Postgres pg_stat_activity view <https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW>`__.
The model contains most of the fields from the view, and the ``cancel`` and ``terminate``
methods can be applied to the queryset.

Setting the Statement Timeout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dynamically set the SQL statement timeout of code using `pgactivity.timeout`:

.. code-block:: python

    import pgactivity

    @pgactivity.timeout(0.5)
    def my_operation():
        # Any queries in this operation that take over 500 milliseconds will throw
        # django.db.utils.OperationalError.

Compatibility
-------------

``django-pgactivity`` is compatible with Python 3.7 -- 3.11, Django 3.2 -- 4.2, Psycopg 2 -- 3 and Postgres 12 -- 15.

Next Steps
----------

We recommend everyone first read:

* :ref:`installation` for how to install the library.

After this, there are several usage guides:

* :ref:`proxy` for an overview of the proxy models and custom queryset methods.
* :ref:`context` for attaching application context to queries.
* :ref:`command` for using and configuring the management command.
* :ref:`timeout` for setting dynamic statement timeouts.

Core API information exists in these sections:

* :ref:`settings` for all available Django settings.
* :ref:`module` for documentation of the ``pgactivity`` module and models.
* :ref:`release_notes` for information about every release.
* :ref:`contributing` for details on contributing to the codebase.
