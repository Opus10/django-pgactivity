import contextlib
import sys
from typing import Any, Callable, List, Union

from django.core.management import execute_from_command_line as django_execute_from_command_line

from pgactivity import runtime


def execute_from_command_line(
    *args: Any,
    ignore_commands: Union[List[str], None] = None,
    exec_func: Union[Callable, None] = None,
    **kwargs: Any,
):
    """
    A drop-in replacement for Django's ``execute_from_command_line`` that attaches
    the command name as context. Can be used in a manage.py file.

    Arguments:
        *args: Args for `exec_func`
        ignore_commands: Command names that should be ignored. Both
            "runserver" and "runserver_plus" are always added to this value.
        exec_func: the function to executed. Defaults to Django's
            `execute_from_command_line` function.
        **kwargs: Kwargs for `exec_func`
    """
    exec_func = exec_func or django_execute_from_command_line
    ignore_commands = ignore_commands or []
    ignore_commands = list(ignore_commands) + ["runserver", "runserver_plus"]

    if len(sys.argv) > 1 and sys.argv[1] not in ignore_commands:
        activity_context = runtime.context(command=sys.argv[1])
    else:  # pragma: no cover
        activity_context = contextlib.ExitStack()

    with activity_context:
        exec_func(*args, **kwargs)
