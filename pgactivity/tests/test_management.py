import random
import threading
import time

from django.core.management import call_command
from django.db import connection
from django.db.utils import OperationalError
import pytest

import pgactivity


@pytest.fixture(autouse=True)
def patch_get_terminal_width(mocker):
    mocker.patch(
        "pgactivity.management.commands.pgactivity.get_terminal_width",
        autospec=True,
        return_value=80,
    )


@pytest.mark.django_db
def test_ls(capsys, reraise):
    call_command("pgactivity", "ls")
    captured = capsys.readouterr()
    assert len(captured.out.split("\n")) >= 2

    call_command("pgactivity", "ls", "-e")
    captured = capsys.readouterr()
    assert len(captured.out.split("\n")) >= 10

    call_command("pgactivity", "ls", "-c", "long-running")
    captured = capsys.readouterr()
    assert len(captured.out.split("\n")) <= 2

    barrier = threading.Barrier(2)
    rand_val = str(random.random())

    @reraise.wrap
    def assert_context_ls():
        barrier.wait()
        time.sleep(0.5)
        call_command("pgactivity", "ls")
        captured = capsys.readouterr()
        assert len(captured.out.split("\n")) >= 3
        assert f"{{'key': '{rand_val}'}}" in captured.out

        call_command("pgactivity", "ls", "-f", f"context__key={rand_val}")
        captured = capsys.readouterr()
        assert len(captured.out.split("\n")) == 2
        assert f"{{'key': '{rand_val}'}}" in captured.out

        call_command("pgactivity", "ls", "-f", "context__key=invalid")
        captured = capsys.readouterr()
        assert len(captured.out.split("\n")) == 1

    @reraise.wrap
    def query_with_context():
        barrier.wait()
        with pgactivity.context(key=1):
            with pgactivity.context(key=rand_val):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_sleep(1);")

    ls = threading.Thread(target=assert_context_ls)
    query = threading.Thread(target=query_with_context)
    ls.start()
    query.start()
    ls.join()
    query.join()


@pytest.mark.django_db
def test_terminate(capsys, reraise):
    barrier = threading.Barrier(2)
    rand_val = str(random.random())

    @reraise.wrap
    def killer_thread():
        barrier.wait()
        time.sleep(0.5)

        call_command("pgactivity", "ls", "-f", f"context__key={rand_val}")
        captured = capsys.readouterr()
        assert len(captured.out.split("\n")) == 2
        assert f"{{'key': '{rand_val}'}}" in captured.out
        pid = captured.out[: captured.out.find("|")]

        call_command("pgactivity", "terminate", pid)

    @reraise.wrap
    def query_to_be_killed():
        barrier.wait()
        with pytest.raises(OperationalError, match="terminating"):
            with pgactivity.context(key=rand_val):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_sleep(1);")

    ls = threading.Thread(target=killer_thread)
    query = threading.Thread(target=query_to_be_killed)
    ls.start()
    query.start()
    ls.join()
    query.join()


@pytest.mark.django_db
def test_cancel(capsys, reraise):
    barrier = threading.Barrier(2)
    rand_val = str(random.random())

    @reraise.wrap
    def killer_thread():
        barrier.wait()
        time.sleep(0.5)

        call_command("pgactivity", "ls", "-f", f"context__key={rand_val}")
        captured = capsys.readouterr()
        assert len(captured.out.split("\n")) == 2
        assert f"{{'key': '{rand_val}'}}" in captured.out
        pid = captured.out[: captured.out.find("|")]

        call_command("pgactivity", "cancel", pid)

    @reraise.wrap
    def query_to_be_killed():
        barrier.wait()
        with pytest.raises(OperationalError, match="canceling"):
            with pgactivity.context(key=rand_val):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_sleep(1);")

    ls = threading.Thread(target=killer_thread)
    query = threading.Thread(target=query_to_be_killed)
    ls.start()
    query.start()
    ls.join()
    query.join()
