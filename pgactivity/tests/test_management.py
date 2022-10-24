import io
import random
import threading
import time

from django.core.management import call_command
from django.db import connection
from django.db.utils import OperationalError
import pytest

import pgactivity
from pgactivity.management.commands import pgactivity as pgactivity_command


@pytest.fixture(autouse=True)
def patch_get_terminal_width(mocker):
    mocker.patch(
        "pgactivity.management.commands.pgactivity.get_terminal_width",
        autospec=True,
        return_value=80,
    )


@pytest.mark.django_db
def test_basic_usage(capsys, reraise, mocker):
    call_command("pgactivity")
    captured = capsys.readouterr()
    assert len(captured.out.split("\n")) >= 2

    call_command("pgactivity", "-e")
    captured = capsys.readouterr()
    assert len(captured.out.split("\n")) >= 10

    call_command("pgactivity", "-c", "long-running")
    captured = capsys.readouterr()
    assert len(captured.out.split("\n")) <= 2

    call_command("pgactivity", "-1")
    captured = capsys.readouterr()
    assert len(captured.out.split("\n")) <= 2

    barrier = threading.Barrier(2)
    rand_val = str(random.random())

    @reraise.wrap
    def assert_context_ls():
        barrier.wait(timeout=5)
        call_command("pgactivity")
        captured = capsys.readouterr()
        assert len(captured.out.split("\n")) >= 3
        assert f"{{'key': '{rand_val}'}}" in captured.out

        call_command("pgactivity", "-f", f"context__key={rand_val}")
        captured = capsys.readouterr()
        assert len(captured.out.split("\n")) == 2
        assert f"{{'key': '{rand_val}'}}" in captured.out

        call_command("pgactivity", "-f", "context__key=invalid")
        captured = capsys.readouterr()
        assert len(captured.out.split("\n")) == 1
        barrier.wait(timeout=5)

    @reraise.wrap
    def query_with_context():
        with pgactivity.context(key=1):
            with pgactivity.context(key=rand_val):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_sleep(0);")
                barrier.wait(timeout=5)
                barrier.wait(timeout=5)

    ls = threading.Thread(target=assert_context_ls)
    query = threading.Thread(target=query_with_context)
    ls.start()
    query.start()
    ls.join()
    query.join()


@pytest.mark.django_db
def test_terminate(capsys, reraise, mocker):
    mocker.patch(
        "pgactivity.management.commands.pgactivity._handle_user_input",
        autospec=True,
        side_effect=[False, True],
    )

    barrier = threading.Barrier(2)
    rand_val = str(random.random())

    @reraise.wrap
    def killer_thread():
        barrier.wait(timeout=5)
        time.sleep(0.25)
        call_command("pgactivity", "-f", f"context__key={rand_val}")
        captured = capsys.readouterr()
        assert len(captured.out.split("\n")) == 2
        assert f"{{'key': '{rand_val}'}}" in captured.out
        pid = captured.out[: captured.out.find("|")]

        with pytest.raises(SystemExit):
            call_command("pgactivity", pid, "--terminate")

        call_command("pgactivity", pid, "--terminate")

    @reraise.wrap
    def query_to_be_killed():
        with pytest.raises(OperationalError, match="terminating"):
            with pgactivity.context(key=rand_val):
                with connection.cursor() as cursor:
                    barrier.wait(timeout=5)
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
        barrier.wait(timeout=5)
        time.sleep(0.25)

        call_command("pgactivity", "-f", f"context__key={rand_val}")
        captured = capsys.readouterr()
        assert len(captured.out.split("\n")) == 2
        assert f"{{'key': '{rand_val}'}}" in captured.out
        pid = captured.out[: captured.out.find("|")]

        call_command("pgactivity", pid, "--cancel", "--yes")

    @reraise.wrap
    def query_to_be_killed():
        with pytest.raises(OperationalError, match="canceling"):
            with pgactivity.context(key=rand_val):
                with connection.cursor() as cursor:
                    barrier.wait(timeout=5)
                    cursor.execute("SELECT pg_sleep(1);")

    ls = threading.Thread(target=killer_thread)
    query = threading.Thread(target=query_to_be_killed)
    ls.start()
    query.start()
    ls.join()
    query.join()


def test_handle_user_input(mocker):
    mocker.patch("builtins.input", lambda *args: "y")
    stdout = io.StringIO()
    assert pgactivity_command._handle_user_input(cfg={}, num_queries=1, stdout=stdout)
    assert not stdout.getvalue()

    mocker.patch("builtins.input", lambda *args: "n")
    stdout = io.StringIO()
    assert not pgactivity_command._handle_user_input(cfg={}, num_queries=1, stdout=stdout)
    assert stdout.getvalue() == "Aborting!"

    stdout = io.StringIO()
    assert pgactivity_command._handle_user_input(cfg={"yes": True}, num_queries=1, stdout=stdout)
    assert not stdout.getvalue()

    stdout = io.StringIO()
    assert not pgactivity_command._handle_user_input(cfg={}, num_queries=0, stdout=stdout)
    assert stdout.getvalue() == "No queries to terminate."

    stdout = io.StringIO()
    assert not pgactivity_command._handle_user_input(
        cfg={"cancel": True}, num_queries=0, stdout=stdout
    )
    assert stdout.getvalue() == "No queries to cancel."
