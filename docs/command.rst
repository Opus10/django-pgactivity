.. _command:

Management Command
==================

Use ``python manage.py pgactivity`` to view, filter, and kill queries.

Basic Usage
-----------

Running ``python manage.py pgactivity`` will show a list of active queries.
Fields are separated by ``|`` and are configured with
``settings.PGACTIVITY_ATTRIBUTES``, which defaults to the following:

1. **id**: The process ID that's running the query.
2. **duration**: The duration of the query.
3. **state**: The state of the query, such as "ACTIVE". See the `Postgres docs <https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW>`__ for values.
4. **context**: Application context tracked by `pgactivity.context`.
5. **query**: The SQL of the query.

Output looks like the following::

    53873 | 2:18:07 | IDLE_IN_TRANSACTION | None | lock table auth_user;
    66747 | 0:16:00 | ACTIVE | None | lock table auth_user;
    68498 | 0:00:00 | ACTIVE | {'command': 'pgactivity'} | WITH _pgactivity_activity_cte AS ( SELEC

.. note::

    Queries are always ordered in descending order by duration.

Use ``-e`` (or ``--expanded``) to avoid truncating results::

    ───────────────────────────────────────────────────────────────────────────────────────────────
    id: 66747
    duration: 0:17:03
    state: ACTIVE
    context: None
    query: lock table auth_user;
    ───────────────────────────────────────────────────────────────────────────────────────────────
    id: 68609
    duration: 0:00:00
    state: ACTIVE
    context: {'command': 'pgactivity'}
    query: WITH
                _pgactivity_activity_cte AS (
                    SELECT
                        pid AS id,
    ...

.. note::

    Query SQL will always be truncated to a max of 1024 characters by
    default unless ``track_activity_query_size`` is configured on your Postgres
    server. We highly recommend attaching context to queries. See the
    :ref:`context` section.

Use ``-f`` (or ``--filter``) to filter results. Below we filter for active queries durations
greater than five seconds::

    python manage.py pgactivity -f "duration__gt=5 seconds" -f state=ACTIVE

.. tip::

    The ``-f`` flag just passes filters to the ``.filter()`` method on the `PGActivity` queryset.
    You can filter on any attribute or relation of the `PGActivity` model.

Canceling and Terminating Queries
---------------------------------

Use ``--cancel`` or ``--terminate`` to issue `pg_cancel_backend <https://www.postgresql.org/docs/9.3/functions-admin.html#FUNCTIONS-ADMIN-SIGNAL-TABLE>`__. or
`pg_terminate_backend <https://www.postgresql.org/docs/9.3/functions-admin.html#FUNCTIONS-ADMIN-SIGNAL-TABLE>`__. requests to all matching results. For example,
the following will terminate every active session, including the
one issuing the management command::

    python manage.py pgactivity --terminate

Normally one will first use the ``pgactivity`` command to find the process
IDs they wish to terminate and then supply them like so::

    python manage.py pgactivity pid1 pid2 --terminate

You'll be prompted before termination and can disable this
with ``-y`` (or ``--yes``).

Re-usable Configurations
------------------------

Use ``settings.PGACTIVITY_CONFIGS`` to store and load re-usable parameters
with ``-c`` (or ``--config``). For example, here we've made a configuration
to cancel all queries that have lasted longer than a minute:

.. code-block:: python

    PGACTIVITY_CONFIGS = {
        "cancel-long-queries": {
            "filters": ["duration__gt=1 minute"],
            "cancel": True,
            "yes": True
        }
    }

We can use this configuration like so::

    python manage.py pgactivity -c cancel-long-queries

.. tip::

    The keys for configuration dictionaries directly match the management command
    argument destinations.
    Do ``python manage.py pgactivity -h`` to see the destinations, which are
    uppercase. Arguments that can be supplied multiple times,
    such as ``-f`` (i.e. the "filters" argument) are provided as lists.

Here's another example of a configuration that changes the output fields of
the ``pgactivity`` command:

.. code-block:: python

    PGACTIVITY_CONFIGS = {
        # Show fields with transaction information
        "transaction-output": {
            "attributes": ["id", "xact_start", "backend_xid"]
        }
    }

When using ``-c transaction-output``, only the process ID, transaction start, and
backend transaction identifier will
be shown by default.

.. tip::

    You can still use a command arguments when using a configuration. 
    Command line arguments override configurations, and configurations
    override global :ref:`settings`.

All Options
-----------

Here's a list of all options to the ``pgactivity`` command:

[pids ...]
    Process IDs to filter by.

-d, --database  The database.
-f, --filter  Filters for the underlying queryset. Can be used multiple times.
-a, --attribute  Attributes to show when listing queries. Defaults to ``settings.PGACTIVITY_ATTRIBUTES``.
-l, --limit  Limit results. Defaults to ``settings.PGACTIVITY_LIMT``.
-e, --expanded   Show an expanded view of results.
-c, --config  Use a config from ``settings.PGACTIVITY_CONFIGS``.
--cancel  Cancel matching activity.
--terminate  Terminate activity.
-y, --yes  Don't prompt when canceling or terminating activity.
