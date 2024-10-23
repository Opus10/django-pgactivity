from typing import Any, List

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, models
from django.db.models.sql import Query
from django.db.models.sql.compiler import SQLCompiler

from pgactivity import config, core, utils


class JSONField(utils.JSONField):
    """A JSONField that has a stable import path.

    Useful for migrations since the JSONField path
    changed in a Django upgrade.
    """

    pass


class PGTableQueryCompiler(SQLCompiler):
    def get_ctes(self):
        context_re = r"^/\*pga_context={[^\*]*}\*/"
        return [
            rf"""
            _pgactivity_activity_cte AS (
                SELECT
                    pid AS id,
                    query_start AS start,
                    NOW() - query_start AS duration,
                    RTRIM(
                        LTRIM(
                            (REGEXP_MATCH(query, '{context_re}'))[1],
                            '/*pga_context='
                        ),
                        '*/'
                    )::jsonb AS context,
                    REGEXP_REPLACE(query, '{context_re}\n', '') AS query,
                    UPPER(REPLACE(state, ' ', '_')) AS state,
                    xact_start,
                    backend_start,
                    backend_xid::text,
                    backend_xmin::text,
                    UPPER(REPLACE(backend_type, ' ', '_')) AS backend_type,
                    TRIM(
                        BOTH '_' FROM UPPER(REGEXP_REPLACE(wait_event_type, '([A-Z])','_\1', 'g'))
                    ) AS wait_event_type,
                    TRIM(
                        BOTH '_' FROM UPPER(REGEXP_REPLACE(wait_event, '([A-Z])','_\1', 'g'))
                    ) AS wait_event,
                    state_change,
                    application_name,
                    client_addr::text,
                    client_hostname,
                    client_port
                    FROM pg_stat_activity
                WHERE
                    datname = '{settings.DATABASES[self.using]["NAME"]}'
                    {self.get_pid_clause()}
            )
            """
        ]

    def get_pid_clause(self):
        pid_clause = ""
        if self.query.pids:
            pid_clause = f"AND pid IN ({', '.join(str(pid) for pid in self.query.pids)})"

        return pid_clause

    def as_sql(self, *args, **kwargs):
        """
        Return a CTE for the pg_stat_activity to facilitate queries
        """
        ctes = "WITH " + ", ".join(self.get_ctes())

        sql, params = super().as_sql(*args, **kwargs)
        return ctes + sql, params


class PGTableQuery(Query):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pids = None

    def get_compiler(self, *args, **kwargs):
        compiler = super().get_compiler(*args, **kwargs)
        compiler.__class__ = PGTableQueryCompiler
        return compiler

    def __chain(self, _name, klass=None, *args, **kwargs):
        clone = getattr(super(), _name)(self.__class__, *args, **kwargs)
        clone.pids = self.pids
        return clone

    def chain(self, klass=None):
        return self.__chain("chain", klass)


class PGTableQuerySet(models.QuerySet):
    """The base queryset for PG* models.

    Allows for the process IDs to be set on the query compiler, making the
    query much more efficient.
    """

    def __init__(self, model=None, query=None, using=None, hints=None):
        if query is None:
            query = PGTableQuery(model)

        super().__init__(model, query, using, hints)

    def pid(self, *pids):
        """Set the PIDs to filter against"""
        qs = self._clone()
        qs.query.pids = [int(pid) for pid in pids]
        return qs


class PGActivityQuerySet(PGTableQuerySet):
    """The Queryset for the `PGActivity` model."""

    def cancel(self) -> List[int]:
        """Cancel filtered activity."""
        pids = list(self.values_list("id", flat=True))
        return core.cancel(*pids, using=self.db)

    def terminate(self) -> List[int]:
        """Terminate filtered activity."""
        pids = list(self.values_list("id", flat=True))
        return core.terminate(*pids, using=self.db)

    def config(self, name: str, **overrides: Any) -> models.QuerySet:
        """
        Use a config name from ``settings.PGACTIVITY_CONFIGS``
        to apply filters. Config overrides can be provided
        in the keyword arguments.

        Args:
            name: Name of the config. Must be a key from ``settings.PGACTIVITY_CONFIGS``.
            **overrides: Any overrides to apply to the final config dictionary.

        Returns:
            dict: The configuration
        """
        qset = self

        cfg = config.get(name, **overrides)

        qset = qset.using(cfg.get("database", DEFAULT_DB_ALIAS))
        qset = qset.pid(*cfg.get("pids", []))

        for f in cfg.get("filters", []) or []:
            key, val = f.split("=", 1)
            qset = qset.filter(**{key: val})

        return qset


class NoObjectsManager(models.Manager):
    """
    Django's dumpdata and other commands will try to dump PG* models.
    This manager is set as the default manager on PG* models to prevent that.
    """

    def get_queryset(self, *args, **kwargs):  # pragma: no cover
        return models.QuerySet(self.model, using=self._db).none()


class PGTable(models.Model):
    no_objects = NoObjectsManager()

    class Meta:
        abstract = True


class PGActivity(PGTable):
    """
    Wraps Postgres's ``pg_stat_activity`` view.

    Attributes:
        start (models.DateTimeField): The start of the query.
        duration (models.DurationField): The duration of the query.
        query (models.TextField): The SQL.
        context (models.JSONField): Context tracked by ``pgactivity.context``.
        state (models.CharField): The state of the query. One of
            ACTIVE, IDLE, IDLE_IN_TRANSACTION, IDLE_IN_TRANSACTION_(ABORTED)
            FASTPATH_FUNCTION_CALL, or DISABLED.
        xact_start (models.DateTimeField): Time when the current
            transaction was started, or null if no transaction is active.
        backend_start (models.DateTimeField): Time when this process was started.
        state_change (models.DateTimeField): Time when the state was last changed.
        wait_event_type (models.CharField): Type of event for which backend is waiting or null.
            `See values here <https://www.postgresql.org/docs/current/monitoring-stats.html#WAIT-EVENT-TABLE>`__.
            Note that values are snake case.
        wait_event (models.CharField): Wait event name if backend is currently waiting.
            `See values here <https://www.postgresql.org/docs/current/monitoring-stats.html#WAIT-EVENT-ACTIVITY-TABLE>`__.
            Note that values are in snake case.
        backend_xid (models.CharField): Top-level transaction identifier of this backend, if any.
        backend_xmin (models.CharField): The current backend's xmin horizon, if any.
        backend_type (models.CharField): One of LAUNCHER, AUTOVACUUM_WORKER,
            LOGICAL_REPLICATION_LAUNCHER, LOGICAL_REPLICATION_WORKER, PARALLEL_WORKER,
            BACKGROUND_WRITER, CLIENT_BACKEND, CHECKPOINTER, ARCHIVER, STARTUP, WALRECEIVER,
            WALSENDER, or WALWRITER.
        application_name (models.CharField): Name of the application that is connected to this backend.
        client_addr (models.CharField): IP address of the client connected to this backend, if any.
        client_hostname (models.CharField): Host name of the connected client, as reported by a
            reverse DNS lookup of client_addr.
        client_port (models.IntegerField): TCP port number that the client is using for
            communication with this backend, or -1 if a Unix socket is used.
    """  # noqa

    start = models.DateTimeField()
    duration = models.DurationField()
    query = models.TextField()
    context = JSONField(null=True)
    state = models.CharField(max_length=64)
    xact_start = models.DateTimeField()
    backend_start = models.DateTimeField()
    state_change = models.DateTimeField()
    wait_event_type = models.CharField(max_length=32, null=True)
    wait_event = models.CharField(max_length=64, null=True)
    backend_xid = models.CharField(max_length=256, null=True)
    backend_xmin = models.CharField(max_length=256, null=True)
    backend_type = models.CharField(max_length=64)
    application_name = models.CharField(max_length=64, null=True)
    client_addr = models.CharField(max_length=256, null=True)
    client_hostname = models.CharField(max_length=256, null=True)
    client_port = models.IntegerField()

    objects = PGActivityQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = "_pgactivity_activity_cte"
        default_manager_name = "no_objects"
