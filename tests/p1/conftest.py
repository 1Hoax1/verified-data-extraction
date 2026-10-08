from pathlib import Path
import pytest
from vde.bootstrap import bootstrap
from vde.config import Config


@pytest.fixture
def env(tmp_path):
    result = bootstrap(Config(tmp_path / "workspace"))
    assert result.health == "ready", result.recovery.errors
    return result


def pytest_collection_modifyitems(items):
    for item in items:
        if item.name.startswith("test_T"):
            number = item.name.split("_", 2)[1][1:]
            item.user_properties.append(("p1_id", "P1-T" + number))
