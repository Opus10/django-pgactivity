import subprocess


def test_execute_from_command_line():
    res = subprocess.run(
        "python manage.py pgactivity ls -f context__command=pgactivity",
        stdout=subprocess.PIPE,
        shell=True,
    )
    assert "{'command': 'pgactivity'}" in res.stdout.decode("utf-8")
