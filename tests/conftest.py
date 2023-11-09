from pas.plugins.oidc.testing import FUNCTIONAL_TESTING
from pas.plugins.oidc.testing import INTEGRATION_TESTING
from pathlib import Path
from pytest_plone import fixtures_factory

import pytest


pytest_plugins = ["pytest_plone"]


globals().update(
    fixtures_factory(
        (
            (INTEGRATION_TESTING, "integration"),
            (FUNCTIONAL_TESTING, "functional"),
        )
    )
)


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Fixture pointing to the docker-compose file to be used."""
    return Path(str(pytestconfig.rootdir)).resolve() / "tests" / "docker-compose.yml"


@pytest.fixture
def wait_for():
    def func(thread):
        if not thread:
            return
        thread.join()

    return func
