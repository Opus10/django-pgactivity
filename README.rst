django-pgactivity
#################

``django-pgactivity`` makes it easy to view, filter, and kill
active Postgres queries.

Some of the features at a glance:

* The ``PGActivity`` proxy model and ``pgactivity`` management command
  for querying and filtering the ``pg_stats_activity`` table.
* ``pgactivity.context`` and ``pgactivity.middleware.ActivityMiddleware``
  for annotating queries with application metadata, such as the request URL.
* ``pgactivity.cancel`` and ``pgactivity.terminate`` for cancelling
  and terminating queries. The ``PGActivity`` model manager also has
  these methods.
* ``pgactivity.timeout`` for dynamically setting the statement timeout.

Quick Start
===========

Use the ``pgactivity ls`` subcommand to see activity queries::

    python manage.py pgactivity ls

Output looks like the following::

    39225 | 0:01:32 | IDLE_IN_TRANSACTION | None | lock auth_user in access exclusiv
    39299 | 0:00:15 | ACTIVE | None | SELECT "auth_user"."id", "auth_user"."password
    39315 | 0:00:00 | ACTIVE | None | WITH _pgactivity_activity_cte AS ( SELECT pid

The columns are as follows:

1. The process ID of the connection.
2. The duration of the query.
3. The state of the query (see the `Postgres docs <https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW>`__ for values).
4. Attached context using ``pgactivity.context``.
5. The query SQL.

Cancel activity with::

    python manage.py pgactivity cancel <process id> <process id> ...

Idle operations such as the first cannot always be cancelled. Terminate the
connection with::

    python manage.py pgactivity terminate <process id> <process id> ...

Decorate your code with ``pgactivity.context`` to attach context to SQL statements.
Install ``pgactivity.middleware.ActivityMiddleware`` to automatically add the
URL and request method to every query. Then you will see values in the
context column::

    39299 | 0:00:15 | ACTIVE | {"url": "/admin/", "method": "GET"} | SELECT "auth_use

Dynamically set the SQL statement timeout of code using ``pgactivity.timeout``:

.. code-block:: python

    import pgactivity

    @pgactivity.timeout(pgactivity.timedelta(milliseconds=500))
    def my_operation():
        # Any queries in this operation that take over 500 milliseconds will throw
        # an exception

Compatibility
=============

``django-pgactivity`` is compatible with Python 3.7 - 3.10, Django 2.2 - 4.1, and Postgres 10 - 15.

Documentation
=============

`View the django-pgactivity docs here
<https://django-pgactivity.readthedocs.io/>`_ for more examples of the management command, configuration
options, context tracking, and the proxy model.

Installation
============

Install django-pgactivity with::

    pip3 install django-pgactivity

After this, add ``pgactivity`` to the ``INSTALLED_APPS``
setting of your Django project.

Contributing Guide
==================

For information on setting up django-pgactivity for development and
contributing changes, view `CONTRIBUTING.rst <CONTRIBUTING.rst>`_.

Primary Authors
===============

- `Wes Kendall <https://github.com/wesleykendall>`__
- `Paul Gilmartin <https://github.com/PaulGilmartin>`__
