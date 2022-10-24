import contextlib
import datetime as dt
import threading

from django.db import connections, DEFAULT_DB_ALIAS
import psycopg2.extensions


_timeout = threading.local()


@contextlib.contextmanager
def timeout(interval=None, *, using=DEFAULT_DB_ALIAS, **timedelta_kwargs):
    """Set the statement timeout as a decorator or context manager.

    A value of 0 means there is no statement timeout.

    Nested invocations will successfully apply and rollback the timeout to
    the previous value.

    Args:
        timeout (Union[datetime.timedelta, int, float], default=None): The number
            of seconds as an integer or float. Use a timedelta object to
            precisely specify the timeout interval.
        using (str, default="default"): The database to use.
        **timedelta_kwargs: Keyword arguments to directly supply to
            datetime.timedelta to create an interval. E.g.
            ``pgactivity.timeout(seconds=1, milliseconds=100)``
            will create a timeout of 1100 milliseconds.

    Raises:
        django.db.utils.OperationalError: When a timeout occurs
    """
    if interval is None:
        interval = dt.timedelta(**timedelta_kwargs)
    elif isinstance(interval, (float, int)):
        interval = dt.timedelta(seconds=interval)

    if not isinstance(interval, dt.timedelta):
        raise TypeError("Must provide a timedelta, int, or float as the interval")

    if not hasattr(_timeout, "value"):
        _timeout.value = None

    old_timeout = _timeout.value
    _timeout.value = int(interval.total_seconds() * 1000)

    try:
        with connections[using].cursor() as cursor:
            cursor.execute(f"SET statement_timeout={_timeout.value}")
            yield
    finally:
        _timeout.value = old_timeout

        with connections[using].cursor() as cursor:
            if (
                not cursor.connection.get_transaction_status()
                == psycopg2.extensions.TRANSACTION_STATUS_INERROR
            ):
                if _timeout.value is None:
                    cursor.execute("RESET statement_timeout")
                else:
                    cursor.execute(f"SET statement_timeout={_timeout.value}")


def _pg_backend_method(method, pids, using):
    assert method in ("cancel", "terminate")

    if pids:
        with connections[using].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT pg_{method}_backend(pid)
                FROM pg_stat_activity
                WHERE pid IN ({', '.join(str(pid) for pid in pids)})
            """
            )

    return pids


def cancel(*pids, using=DEFAULT_DB_ALIAS):
    """Cancel activity using the Postgres ``pg_cancel_backend`` function.

    Args:
        *pids (int): The process ID(s) to cancel.
        using (str, default="default"): The database to use.

    Returns:
        List[int]: Canceled process IDs
    """
    return _pg_backend_method("cancel", pids, using)


def terminate(*pids, using=DEFAULT_DB_ALIAS):
    """Terminate activity using the Postgres ``pg_teminate_backend`` function.

    Args:
        *pids (int): The process ID(s) to terminate.
        using (str, default="default"): The database to use.

    Returns:
        List[int]: Terminated process IDs
    """
    return _pg_backend_method("terminate", pids, using)


def pid(using=DEFAULT_DB_ALIAS):
    """Get the current backend process ID.

    Args:
        using (str, default="default"): The database to use.

    Returns:
        int: The current backend process ID
    """
    with connections[using].cursor() as cursor:
        cursor.execute("SELECT pg_backend_pid()")
        return cursor.fetchone()[0]
