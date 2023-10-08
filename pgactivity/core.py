import contextlib
import datetime as dt
import threading
from typing import List, Union

from django.db import DEFAULT_DB_ALIAS, connections

from pgactivity import utils

if utils.psycopg_maj_version == 2:
    import psycopg2.extensions
elif utils.psycopg_maj_version == 3:
    import psycopg.pq
else:
    raise AssertionError


_timeout = threading.local()
_unset = object()


def _cast_timeout(timeout):
    if isinstance(timeout, (int, float)):
        timeout = dt.timedelta(seconds=timeout)

    if not isinstance(timeout, dt.timedelta):
        raise TypeError("Must supply int, float, or timedelta to pgactivity.timeout")

    if timeout < dt.timedelta(milliseconds=1):
        timeout = dt.timedelta()

    return timeout


def _is_transaction_errored(cursor):
    """
    True if the current transaction is in an errored state
    """
    if utils.psycopg_maj_version == 2:
        return (
            cursor.connection.get_transaction_status()
            == psycopg2.extensions.TRANSACTION_STATUS_INERROR
        )
    elif utils.psycopg_maj_version == 3:
        return cursor.connection.info.transaction_status == psycopg.pq.TransactionStatus.INERROR
    else:
        raise AssertionError


@contextlib.contextmanager
def timeout(
    timeout: Union[dt.timedelta, int, float, None] = _unset,
    *,
    using: str = DEFAULT_DB_ALIAS,
    **timedelta_kwargs: int,
):
    """Set the statement timeout as a decorator or context manager.

    A value of ``None`` will set an infinite statement timeout.
    A value of less than a millisecond is not permitted.

    Nested invocations will successfully apply and rollback the timeout to
    the previous value.

    Args:
        timeout: The number of seconds as an integer or float. Use a timedelta
            object to precisely specify the timeout interval. Use ``None`` for
            an infinite timeout.
        using: The database to use.
        **timedelta_kwargs: Keyword arguments to directly supply to
            datetime.timedelta to create an interval. E.g.
            `pgactivity.timeout(seconds=1, milliseconds=100)`
            will create a timeout of 1100 milliseconds.

    Raises:
        django.db.utils.OperationalError: When a timeout occurs
        TypeError: When the timeout interval is an incorrect type
    """
    if timedelta_kwargs:
        timeout = dt.timedelta(**timedelta_kwargs)
    elif timeout is _unset:
        raise ValueError("Must supply a value to pgactivity.timeout")

    if timeout is not None:
        timeout = _cast_timeout(timeout)

        if not timeout:
            raise ValueError(
                "Must supply value greater than a millisecond to pgactivity.timeout"
                " or use ``None`` to reset the timeout."
            )
    else:
        timeout = dt.timedelta()

    if not hasattr(_timeout, "value"):
        _timeout.value = None

    old_timeout = _timeout.value
    _timeout.value = int(timeout.total_seconds() * 1000)

    try:
        with connections[using].cursor() as cursor:
            cursor.execute(f"SELECT set_config('statement_timeout', '{_timeout.value}', false)")
            yield
    finally:
        _timeout.value = old_timeout

        with connections[using].cursor() as cursor:
            if not _is_transaction_errored(cursor):
                if _timeout.value is None:
                    cursor.execute("SELECT set_config('statement_timeout', NULL, false)")
                else:
                    cursor.execute(
                        f"SELECT set_config('statement_timeout', '{_timeout.value}', false)"
                    )


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


def cancel(*pids: int, using: str = DEFAULT_DB_ALIAS) -> List[int]:
    """Cancel activity using the Postgres ``pg_cancel_backend`` function.

    Args:
        *pids: The process ID(s) to cancel.
        using: The database to use.

    Returns:
        Canceled process IDs
    """
    return _pg_backend_method("cancel", pids, using)


def terminate(*pids: int, using: str = DEFAULT_DB_ALIAS) -> List[int]:
    """Terminate activity using the Postgres ``pg_teminate_backend`` function.

    Args:
        *pids: The process ID(s) to terminate.
        using: The database to use.

    Returns:
        Terminated process IDs
    """
    return _pg_backend_method("terminate", pids, using)


def pid(using: str = DEFAULT_DB_ALIAS) -> int:
    """Get the current backend process ID.

    Args:
        using: The database to use.

    Returns:
        The current backend process ID
    """
    with connections[using].cursor() as cursor:
        cursor.execute("SELECT pg_backend_pid()")
        return cursor.fetchone()[0]
