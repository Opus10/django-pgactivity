import contextlib
import datetime as dt
import threading
import warnings

from django.db import connections, DEFAULT_DB_ALIAS


_timeout = threading.local()


@contextlib.contextmanager
def timeout(interval, using=DEFAULT_DB_ALIAS):
    """Set the statement timeout.

    Cannot be nested. If in a transaction and the transaction is in an
    errored state, the variable will not be flushed
    and will exist until the transaction is finished.

    Args:
        interval (`datetime.timedelta`): The timeout interval.
            Use `pgactivity.timedelta` as a shortcut to avoid
            importing the datetime module.
        using (str, default="default"): The database.
    """
    assert isinstance(interval, dt.timedelta)

    if not hasattr(_timeout, "value"):
        _timeout.value = None

    if _timeout.value is not None:
        raise RuntimeError("Calls to pgactivity.timeout cannot be nested")

    _timeout.value = int(interval.total_seconds() * 1000)
    local = connections[using].in_atomic_block

    try:
        with connections[using].cursor() as cursor:
            cursor.execute(f"SET {'LOCAL' if local else ''} statement_timeout={_timeout.value}")
            yield
    finally:
        _timeout.value = None

        if local and connections[using].errors_occurred:
            warnings.warn(
                "pgactivity.timeout() cannot flush variable because the transaction is errored."
                " It will leak until the transaction is rolled back."
            )
        else:
            with connections[using].cursor() as cursor:
                cursor.execute("RESET statement_timeout")


def cancel(*pids, using=DEFAULT_DB_ALIAS):
    """Cancel activity using the Postgres ``pg_cancel_backend`` function.

    Args:
        *pids (int): The process ID(s) to cancel.
        using (str, default="default"): The database to use.
    """
    if pids:
        with connections[using].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT pg_cancel_backend(pid)
                FROM pg_stat_activity
                WHERE pid IN ({', '.join(str(pid) for pid in pids)})
            """
            )

    return pids


def terminate(*pids, using=DEFAULT_DB_ALIAS):
    """Terminate activity using the Postgres ``pg_teminate_backend`` function.

    Args:
        *pids (int): The process ID(s) to terminate.
        using (str, default="default"): The database to use.
    """
    if pids:
        with connections[using].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE pid IN ({', '.join(str(pid) for pid in pids)})
            """
            )

    return pids


def pid(using=DEFAULT_DB_ALIAS):
    """Get the current backend process ID.

    Args:
        using (str, default="default"): The database to use.
    """
    with connections[using].cursor() as cursor:
        cursor.execute("SELECT pg_backend_pid()")
        return cursor.fetchone()[0]
