.. _usage:

Usage
=====

``PGActivity`` Model
---------------------

The foundation of ``django-pgactivity`` is the `PGActivity` model.
It's a wrapper around the `pg_stat_activity Postgres table <https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW>`__
with additional goodies.

Query all current activity like so:

.. code-block:: python

    from pgactivity.models import PGActivity

    PGActivity.objects.all()

The following fields can be filtered:

* **id**: The process ID of the query.
* **start**: The start time of the query.
* **duration**: The duration of the query.
* **query**: The query SQL. By default Postgres only stores the first 1024 characters. This can be configured
  with the `track_activity_query_size Postgres configuration variable <https://www.postgresql.org/docs/current/runtime-config-statistics.html#GUC-TRACK-ACTIVITY-QUERY-SIZE>`__.
* **state**: The state of the query. See the `pg_stat_activity Postgres docs for possible fields <https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW>`__
* **context**: A JSON field with context attached using the `pgactivity.context` decorator. More on this later.

Although it's possible to filter directly by ``id`` to see the activity of a process,
we recommend using the ``pid()`` method to construct a more optimized query underneath
the hood like so:

.. code-block::

    PGActivity.objects.pid(10234, 34132).filter(...)

`PGActivity` comes with ``cancel()`` and ``terminate()`` methods on the queryset to issue
`pg_cancel_backend <https://www.postgresql.org/docs/9.3/functions-admin.html#FUNCTIONS-ADMIN-SIGNAL-TABLE>`__
or `pg_terminate_backend <https://www.postgresql.org/docs/9.3/functions-admin.html#FUNCTIONS-ADMIN-SIGNAL-TABLE>`__
operations on the matching process IDs.

``pgactivity`` Command
----------------------

The ``pgactivity`` management command consists of three subcommands:

1. **ls**: For listing queries.
2. **cancel**: For cancelling queries.
3. **terminate**: For terminating queries.

Listing Queries
~~~~~~~~~~~~~~~

Here are the options for ``ls``:

[pids ...]
    Only list these process IDs.

-d, --database  Use this database. Defaults to the "default" database.
-f, --filter  Filter queries. Can be supplied multiple times.
-l, --limit  Limit the results. Uses ``settings.PGACTIVITY_LIMIT``
             as the default, which defaults to 25.
-e, --expanded  Show an expanded view without truncating results.
-c, --config  Use a stored configuration of parameters as defaults.

The output of ``ls`` has the following columns from the `PGActivity` model: id,
duration, state, context, and query.

When applying filters, use keys and values that can be supplied
to the queryset's ``filter()`` method. For example, filter
by state with::

    python manage.py pgactivity ls -f state=ACTIVE

You can pass human-readable arguments to filter by duration. Here we filter
by state and by duration::

    python manage.py pgactivity ls -f state=ACTIVE -f 'duration__gt=3 minutes'

Re-using Configuration
~~~~~~~~~~~~~~~~~~~~~~

Using many filters and redundant arguments can be cumbersome. Arguments
to the ``ls`` command can be stored in the ``settings.PGACTIVITY_CONFIGS``
setting. For example, here we've defined a config called "long-running"
that saves the arguments for displaying long-running queries:

.. code-block:: python

    PGACTIVITY_CONFIGS = {
        "long-running": {
            "filters": ["duration__gte=1 minute"]
        }
    }

The config can be used like so::

    python manage.py pgactivity ls -c long-running

.. tip::

    Any argument to the ``ls`` command can be stored in a config, such
    as ``database``, ``expanded``, and ``limit``.

Cancelling and Terminating Queries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cancel queries using the process ID of the activity (i.e. the id field)::

    python manage.py pgactivity cancel 12354 23147 ...

Terminate queries using the same arguments::

    python manage.py pgactivity terminate 12354 23147 ...

Attaching Context
-----------------

When viewing active queries, it can be difficult to understand where
the query originates. The `pgactivity.context` function and
associated middleware solves this by attaching metadata to the generated SQL.

For example, when the below function is called, ``{"key": "value"}``
will be added as a comment at the top of the SQL, and ``django-pgactivity``
parses this into the ``context`` field of the `PGActivity` model:

.. code-block:: python

    import pgactivity

    @pgactivity.context(key="value")
    def some_query():
        # Any SQL issued here will have context associated with it.

.. note::

    By default, Django's JSON encoder is used. You can configure
    the JSON encoder path with ``settings.PGACTIVITY_JSON_ENCODER``
    if encoding custom objects.

You can filter on individual context keys. For example,
``PGActivity.objects.filter(context__key="value")`` will
show all activity from the example function above.
The same applies for using the management command::

    python manage.py pgactivity ls -f context__key=value

Next are ways you can automatically attach context from
requests, management commands,
and background tasks.

Requests
~~~~~~~~

Add `pgactivity.middleware.ActivityMiddleware`
to ``settings.MIDDLEWARE`` to automatically track
both the ``url`` and ``method`` for every request, allowing you to see which
URL issued a query. This can be helpful when determining
if it's safe to kill a particular query.

Management Commands
~~~~~~~~~~~~~~~~~~~

One-off management commands that don't go through requests can
be instrumented in the ``manage.py`` file
using `pgactivity.contrib.execute_from_command_line`, which
is a wrapper of Django's ``execute_from_command_line``:

.. code-block:: python

    #!/usr/bin/env python
    import os
    import sys


    if __name__ == "__main__":
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
        from pgactivity.contrib import execute_from_command_line

        execute_from_command_line(sys.argv)

.. note::

    `pgactivity.contrib.execute_from_command_line` ignores ``runserver`` and ``runserver_plus``
    by default. Add more commands using the ``ignore_commands`` keyword argument.
    The ``exec_func`` argument can also supply a custom exec function.

If it's not possible to use `pgactivity.contrib.execute_from_command_line`
in your ``manage.py``, you can achieve the same functionality like so:

.. code-block:: python

    import contextlib
    import sys
    from django.core.management import execute_from_command_line


    ignore_commands = ["runserver", "runserver_plus"]

    if len(sys.argv) > 1 and not sys.argv[1] in ignore_commands:
        activity_context = runtime.context(command=sys.argv[1])
    else:
        activity_context = contextlib.ExitStack()

    with activity_context:
        execute_from_command_line(sys.argv)

Celery Tasks
~~~~~~~~~~~~

Celery tasks can also be instrumented like so:

.. code-block:: python

    import celery
    import pgactivity

    class Task(celery.Task):
        def __call__(self, *args, **kwargs):
            with pgactivity.context(task=self.name):
                return super().__call__(*args, **kwargs)


    # Override the celery task decorator for your application
    app = create_celery_app('my-app')
    task = app.task(base=Task)

Setting Statement Timeouts
--------------------------

Using the `pgactivity.timeout` decorator and context manager to dynamically
set Postgres's ``statement_timeout`` setting.

For example, the following code ensures that no single query takes longer than
500 milliseconds:

.. code-block:: python

    import pgactivity

    with pgactivity.timeout(pgactivity.timedelta(milliseconds=500)):
        # Issue queries. Any that exceed 500 milliseconds will raise an exception

.. note::

    `pgactivity.timedelta` is just a shortcut for Python's `datetime.timedelta`.

The statement timeout will be applied locally to the connection and will
not affect other queries. It can also be used as a decorator.

.. warning::

    `pgactivity.timeout` cannot be nested and will raise a `RuntimeError` if
    it is nested. If running in a transaction and the transaction errors
    before `pgactivity.timeout` exits, a warning will be printed and the
    Postgres variable will not be flushed until the transaction is finished.
    This can be prevented by wrapping the inner code in
    Django's ``transaction.atomic()``.
