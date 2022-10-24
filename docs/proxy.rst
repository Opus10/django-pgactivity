.. _proxy:

PGActivity Model
================

The foundation of ``django-pgactivity`` is the `PGActivity` model.
It's a wrapper around the `pg_stat_activity Postgres view <https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW>`__
with additional goodies.

Query all current activity like so:

.. code-block:: python

    from pgactivity.models import PGActivity

    PGActivity.objects.all()

Here are some of the fields that can be queried:

* **id**: The process ID of the query.
* **start**: The start time of the query.
* **duration**: The duration of the query.
* **query**: The query SQL. By default Postgres only stores the first 1024 characters. This can be configured
  with the `track_activity_query_size Postgres configuration variable <https://www.postgresql.org/docs/current/runtime-config-statistics.html#GUC-TRACK-ACTIVITY-QUERY-SIZE>`__.
* **state**: The state of the query. See the `pg_stat_activity Postgres docs for possible fields <https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW>`__
* **context**: A JSON field with context attached using the `pgactivity.context` decorator. More on this later.

See `PGActivity` for a list of every field, which also includes transaction and client information.

There are some special queryset methods worth noting:

* ``PGActivity.objects.pid(pid1, pid2)``: Filter based on the process ID. Although it's possible to filter on ``id`` directly,
  using the ``pid`` method results in a more efficient query.
* ``PGActivity.objects.filter(...).cancel()``: Cancels all matching queries using `pg_cancel_backend <https://www.postgresql.org/docs/9.3/functions-admin.html#FUNCTIONS-ADMIN-SIGNAL-TABLE>`__.
* ``PGActivity.objects.filter(...).terminate()``: Terminates all matching queries using `pg_terminate_backend <https://www.postgresql.org/docs/9.3/functions-admin.html#FUNCTIONS-ADMIN-SIGNAL-TABLE>`__.

When querying the SQL, remember that it's truncated to 1024 characters by default and can only be
changed by adjusting the global ``track_activities_query_size`` Postgres setting. In order to better
understand where queries originate, see the :ref:`context` section.