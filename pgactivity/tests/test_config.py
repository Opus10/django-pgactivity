import pytest

from pgactivity import config


def test_name_invalid():
    with pytest.raises(ValueError, match="not a valid config"):
        config.get("invalid")
