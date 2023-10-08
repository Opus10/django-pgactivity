# Annotating Query Context

It can be difficult to understand where queries originate in an application by just examining the SQL. The [pgactivity.context][] function and associated middleware solves this by attaching metadata to the generated SQL. In other words, the SQL executed by your application will have comments added to it that can be parsed by `django-pgactivity`.

## Basic Usage

Below we attach the task name to all SQL executed in a function:

```python
import pgactivity

@pgactivity.context(task="task_name")
def my_func():
    # All SQL executed will have "task: task_name" annotated as a SQL comment
```

This metadata now appears in the `context` field of the `PGActivity` model, allowing us to view it and filter by it. For example, the following will return all queries from our function:

```python
from pgactivity.models import PGActivity

PGActivity.objects.filter(context__task="task_name")
```

The same applies for using the management command:

    python manage.py pgactivity -f context__task=task_name

Context collection can be nested too:

```python
import pgactivity

with pgactivity.context(my="context"):
    # Do stuff...

    with pgactivity.context(other="stuff"):
        # Do stuff. Both the "my" and "other" keys will be in context

    # Only the "my" key will be in the context for
    # SQL statements here
```

!!! note

    By default, Django's JSON encoder is used to serialize keys and values SQL comments. You can configure the JSON encoder path with `settings.PGACTIVITY_JSON_ENCODER` to encode custom objects.

Next are ways you can automatically attach context from requests, management commands, and background tasks.

## Tracking Requests with Middleware

Add [pgactivity.middleware.ActivityMiddleware][] to `settings.MIDDLEWARE` to automatically track both the `url` and `method` for every request, allowing you to see which URL issued a query. This can be helpful when determining if it's safe to kill a particular query.

## Management Commands

One-off management commands that don't go through requests can be instrumented in the `manage.py` file using `pgactivity.contrib.execute_from_command_line`, which is a wrapper of Django's `execute_from_command_line`:

```python
#!/usr/bin/env python
import os
import sys


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    from pgactivity.contrib import execute_from_command_line

    execute_from_command_line(sys.argv)
```

!!! note

    [pgactivity.contrib.execute_from_command_line][] ignores `runserver` and `runserver_plus` by default. Add more commands using the `ignore_commands` keyword argument. The `exec_func` argument can also supply a custom exec function.

If it's not possible to use [pgactivity.contrib.execute_from_command_line][] in your `manage.py`, you can achieve the same functionality like so:

```python
import contextlib
import sys
from django.core.management import execute_from_command_line


ignore_commands = ["runserver", "runserver_plus"]

if len(sys.argv) > 1 and not sys.argv[1] in ignore_commands:
    activity_context = runtime.context(command=sys.argv[1])
else:
    activity_context = contextlib.ExitStack()

with activity_context:
    execute_from_command_line(sys.argv)
```

## Celery Tasks

Celery tasks can also be instrumented like so:

```python
import celery
import pgactivity

class Task(celery.Task):
    def __call__(self, *args, **kwargs):
        with pgactivity.context(task=self.name):
            return super().__call__(*args, **kwargs)


# Override the celery task decorator for your application
app = create_celery_app('my-app')
task = app.task(base=Task)
```