"""Core way to access configuration"""

from django.conf import settings
from django.utils.module_loading import import_string


def attributes():
    return getattr(
        settings,
        "PGACTIVITY_ATTRIBUTES",
        [
            "id",
            "duration",
            "state",
            "context",
            "query",
        ],
    )


def configs():
    """Return pre-configured LS arguments"""
    return getattr(settings, "PGACTIVITY_CONFIGS", {})


def limit():
    """The default limit when using the LS subcommand"""
    return getattr(settings, "PGACTIVITY_LIMIT", 25)


def get(name, **overrides):
    """Get a configuration with overrides"""
    if not name:
        cfg = {}
    elif name not in configs():
        raise ValueError(f'"{name}" is not a valid config name from settings.PGACTIVITY_CONFIGS')
    else:
        cfg = configs()[name]

    if "limit" not in cfg:
        cfg["limit"] = limit()

    if "attributes" not in cfg:
        cfg["attributes"] = attributes()

    # Note: We might allow overriding with "None" or empty values later, but currently no
    # settings allow this. This code filters overrides so that management commands can
    # simply pass in options that might already contain Nones
    cfg.update(**{key: val for key, val in overrides.items() if val})

    return cfg


def json_encoder():
    """The JSON encoder when tracking context"""
    encoder = getattr(
        settings, "PGACTIVITY_JSON_ENCODER", "django.core.serializers.json.DjangoJSONEncoder"
    )

    if isinstance(encoder, str):  # pragma: no branch
        encoder = import_string(encoder)

    return encoder
