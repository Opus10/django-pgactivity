# Settings

Below are all settings for `django-pgactivity`.

## PGACTIVITY_ATTRIBUTES

The default attributes of the `PGActivity` model shown by the `pgactivity` management command.

**Default** `( "id", "duration", "state", "context", "query")`

## PGACTIVITY_CONFIGS

Re-usable configurations that can be supplied to the `pgactivity` command with the `-c` option. Configurations are referenced by their key in the dictionary.

For example:

```python
PGACTIVITY_CONFIGS = {
    "long-running": {
        "filters": ["wait_duration__gt=1 minute"]
    }
}
```

Doing `python manage.py pgactivity -c long-running` will only show queries duration greater than a minute.

**Default** `{}`

## PGACTIVITY_JSON_ENCODER

Used to encode JSON when tracking context.

**Default** `"django.core.serializers.json.DjangoJSONEncoder"`

## PGACTIVITY_LIMIT

Limit the results returned by the `pgactivity` command. Can be overridden with the `-l` option.

**Default** `25`
