import threading
import time

import ddf
import pytest
from django.core.management import call_command
from django.db import connection, transaction
from django.db.utils import OperationalError

import pgactivity


@pytest.mark.django_db
def test_middleware(client, capsys, reraise):
    user = ddf.G("auth.User")
    client.force_login(user)

    barrier3 = threading.Barrier(3)
    barrier2 = threading.Barrier(2)

    @reraise.wrap
    def lock_user_table():
        """Lock the user table so the admin will stall"""
        with pytest.raises(OperationalError, match="statement timeout"):
            with pgactivity.timeout(pgactivity.timedelta(seconds=1)):
                with connection.cursor() as cursor, transaction.atomic():
                    barrier3.wait(timeout=5)
                    cursor.execute("LOCK auth_user IN ACCESS EXCLUSIVE MODE")

    @reraise.wrap
    def load_admin():
        """The admin will stall since the user table is locked"""
        barrier3.wait(timeout=5)
        time.sleep(0.25)
        client.get("/admin/")
        barrier2.wait(timeout=5)

    @reraise.wrap
    def check_middleware():
        barrier3.wait(timeout=5)
        time.sleep(0.5)
        call_command("pgactivity", "-f", "context__url=/admin/")
        captured = capsys.readouterr()
        assert "'url': '/admin/'" in captured.out
        barrier2.wait(timeout=5)

    lock_user_table_thread = threading.Thread(target=lock_user_table)
    load_admin_thread = threading.Thread(target=load_admin)
    check_middleware_thread = threading.Thread(target=check_middleware)
    lock_user_table_thread.start()
    load_admin_thread.start()
    check_middleware_thread.start()
    lock_user_table_thread.join()
    load_admin_thread.join()
    check_middleware_thread.join()
