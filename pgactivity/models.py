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
    def get_ctes(self, pid_clause):
        context_re = r"^/\*pga_context={[^\*]*}\*/"
        return [
            f"""
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
                    UPPER(REPLACE(state, ' ', '_')) AS state
                    FROM pg_stat_activity
                WHERE datname = '{settings.DATABASES[self.using]["NAME"]}' {pid_clause}
            )
            """
        ]

    def as_sql(self, *args, **kwargs):
        """
        Return a CTE for the pg_stat_activity to facilitate queries
        """
        pid_clause = ""
        if self.query.pids:
            pid_clause = f"AND pid IN ({', '.join(str(pid) for pid in self.query.pids)})"

        ctes = "WITH " + ", ".join(self.get_ctes(pid_clause))

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
        qs.query.pids = pids
        return qs


class PGActivityQuerySet(PGTableQuerySet):
    def cancel(self):
        """Cancel filtered activity."""
        pids = list(self.values_list("id", flat=True))
        return core.cancel(*pids, using=self.db)

    def terminate(self):
        """Terminate filtered activity."""
        pids = list(self.values_list("id", flat=True))
        return core.terminate(*pids, using=self.db)

    def config(self, name, **overrides):
        """
        Use a config name from ``settings.PGACTIVITY_CONFIGS``
        to apply filters. Config overrides can be provided
        in the keyword arguments.
        """
        qset = self

        cfg = config.get(name, **overrides)

        qset = qset.using(cfg.get("database", DEFAULT_DB_ALIAS))
        qset = qset.pid(*cfg.get("pids", []))

        for f in cfg.get("filters", []) or []:
            key, val = f.split("=", 1)
            qset = qset.filter(**{key: val})

        if not cfg.get("pids") and cfg.get("limit"):  # pragma: no branch
            qset = qset[: cfg["limit"]]

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
    A proxy model that wraps the ``pg_stat_activity`` table.
    """

    start = models.DateTimeField()
    duration = models.DurationField()
    query = models.TextField()
    context = JSONField(null=True)
    state = models.CharField(max_length=64)

    objects = PGActivityQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = "_pgactivity_activity_cte"
        default_manager_name = "no_objects"
