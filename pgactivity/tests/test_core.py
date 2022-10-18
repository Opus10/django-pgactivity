import ddf
from django.db import connection, transaction
from django.db.utils import OperationalError
import pytest

import pgactivity


@pytest.mark.django_db
def test_timeout_no_nested():
    with pgactivity.timeout(pgactivity.timedelta(milliseconds=100)):
        with pytest.raises(RuntimeError, match="cannot be nested"):
            with pgactivity.timeout(pgactivity.timedelta(milliseconds=100)):
                pass


@pytest.mark.django_db
def test_timeout_in_transaction():
    with pgactivity.timeout(pgactivity.timedelta(milliseconds=500)):
        ddf.G("auth.User")

    with pytest.raises(OperationalError, match="timeout"), transaction.atomic():
        with pgactivity.timeout(pgactivity.timedelta(milliseconds=200)):
            with connection.cursor() as cursor:
                cursor.execute("select pg_sleep(1)")

    with pytest.raises(OperationalError, match="timeout"):
        with pgactivity.timeout(pgactivity.timedelta(milliseconds=200)):
            with connection.cursor() as cursor:
                cursor.execute("select pg_sleep(1)")


@pytest.mark.django_db(transaction=True)
def test_timeout_not_in_transaction():
    with pgactivity.timeout(pgactivity.timedelta(milliseconds=500)):
        ddf.G("auth.User")

    with pytest.raises(OperationalError, match="timeout"):
        with pgactivity.timeout(pgactivity.timedelta(milliseconds=200)):
            with connection.cursor() as cursor:
                cursor.execute("select pg_sleep(1)")


@pytest.mark.django_db
def test_cancel():
    """Verifies validity of SQL for pgactivity.cancel"""
    assert not pgactivity.cancel()
    assert pgactivity.cancel(1000000000)


@pytest.mark.django_db
def test_terminate():
    """Verifies validity of SQL for pgactivity.terminate"""
    assert not pgactivity.terminate()
    assert pgactivity.terminate(1000000000)


@pytest.mark.django_db
def test_pid():
    pid = pgactivity.pid()
    assert isinstance(pid, int)
