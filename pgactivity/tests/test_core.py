import ddf
from django.contrib.auth.models import User
from django.db import connection, transaction
from django.db.utils import IntegrityError
import pytest

import pgactivity


@pytest.mark.django_db(transaction=True)
def test_timeout():
    ddf.G("auth.User", username="hello")

    def get_timeout():
        with connection.cursor() as cursor:
            cursor.execute("SHOW statement_timeout")
            return cursor.fetchone()[0]

    with pgactivity.timeout(1):
        assert get_timeout() == "1s"

        with pgactivity.timeout(seconds=2):
            assert get_timeout() == "2s"

            try:
                with transaction.atomic():  # pragma: no branch
                    with pgactivity.timeout(seconds=3):
                        assert get_timeout() == "3s"

                    assert get_timeout() == "2s"

                    with pgactivity.timeout(seconds=4):
                        assert get_timeout() == "4s"

                        try:
                            with transaction.atomic():  # pragma: no branch
                                with pgactivity.timeout(seconds=5):
                                    assert get_timeout() == "5s"
                                    User.objects.create(username="hello")
                        except IntegrityError:
                            pass

                        assert get_timeout() == "4s"

                    with pgactivity.timeout(seconds=6):
                        User.objects.create(username="hello")
            except IntegrityError:
                pass

            assert get_timeout() == "2s"

        assert get_timeout() == "1s"


def test_timeout_args():
    with pytest.raises(TypeError, match="provide a"):
        with pgactivity.timeout("1"):
            pass


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
