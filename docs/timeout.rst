.. _timeout:

Setting the Statment Timeout
============================

Use `pgactivity.timeout` to dynamically set Postgres's ``statement_timeout`` variable.
This setting is isolated to the thread executing code.

For example, below we've ensured that no statement will take longer
than three seconds to run:

.. code-block:: python

    import pgactivity

    with pgactivity.timeout(3):
        # If any SQL statement takes longer than 3 seconds to run,
        # a django.db.utils.OperationalError will be raised.

.. note::

    A timeout of zero means there will be no statement timeout.

`pgactivity.timeout` can be nested like so:

.. code-block:: python

    with pgactivity.timeout(2):
        # Every statment here will have a lock timeout of 2 seconds

        with pgactivity.timeout(5):
            # Every statement will now have a lock timeout of 5 seconds

        # Statements here will have a lock timeout of 2 seconds

Remember, `pgactivity.timeout` can also be used as a decorator.

.. tip::

    Pass a Python ``datetime.timedelta`` object to `pgactivity.timeout` for more precision
    or use the ``seconds`` and ``milliseconds`` options of `pgactivity.timeout`.
