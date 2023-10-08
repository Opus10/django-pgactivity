import contextlib
import json
import threading

from django.db import connection

from pgactivity import config

_context = threading.local()


def _inject_context(execute, sql, params, many, context):
    # Metadata is stored as a serialized JSON string and added as
    # a top-level comment to the SQL. This comment can be parsed
    # by the `PGActivity` model.
    metadata_str = json.dumps(_context.value, cls=config.json_encoder())
    sql = f"/*pga_context={metadata_str.replace('*', '-')}*/\n" + sql
    return execute(sql, params, many, context)


class context(contextlib.ContextDecorator):
    """
    A context manager that adds additional metadata to SQL statements.

    Once any code has entered ``pgactivity.context``, all subsequent
    entrances of ``pgactivity.context`` will be overwrite keys.

    To add context only if a parent has already entered ``pgactivity.context``,
    one can call ``pgactivity.context`` as a function without entering it.
    The metadata set in the function call will be part of the context if
    ``pgactivity.context`` has previously been entered. Otherwise it will
    be ignored.

    Args:
        metadata (dict): Metadata that should be attached to the activity
            context

    Example:
        Here we track a "key" with a value of "value"::

            with pgactivity.context(key='value'):
                # Do things..
                # All SQL will have a {'key': 'value'} metadata comment.
                # Nesting will add additional metadata to the current
                # context

            # Add metadata if a parent piece of code has already entered
            # pgactivity.context
            pgactivity.context(key='value')
    """

    def __init__(self, **metadata):
        self.metadata = metadata
        self._pre_execute_hook = None

        if hasattr(_context, "value"):
            _context.value.update(**self.metadata)

    def __enter__(self):
        if not hasattr(_context, "value"):
            self._pre_execute_hook = connection.execute_wrapper(_inject_context)
            self._pre_execute_hook.__enter__()
            _context.value = self.metadata

        return _context.value

    def __exit__(self, *exc):
        if self._pre_execute_hook:
            delattr(_context, "value")
            self._pre_execute_hook.__exit__(*exc)
