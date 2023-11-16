from pas.plugins.oidc.testing import FUNCTIONAL_TESTING
from pas.plugins.oidc.testing import INTEGRATION_TESTING
from pas.plugins.oidc.testing import RESTAPI_TESTING
from pathlib import Path
from pytest_plone import fixtures_factory
from requests.exceptions import ConnectionError

import pytest
import requests


pytest_plugins = ["pytest_plone"]


globals().update(
    fixtures_factory(
        (
            (INTEGRATION_TESTING, "integration"),
            (FUNCTIONAL_TESTING, "functional"),
            (RESTAPI_TESTING, "restapi"),
        )
    )
)


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Fixture pointing to the docker-compose file to be used."""
    return Path(str(pytestconfig.rootdir)).resolve() / "tests" / "docker-compose.yml"


def is_responsive(url: str) -> bool:
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True
    except ConnectionError:
        return False


@pytest.fixture(scope="session")
def keycloak_service(docker_ip, docker_services):
    """Ensure that keycloak service is up and responsive."""
    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("keycloak", 8080)
    url = f"http://{docker_ip}:{port}"
    docker_services.wait_until_responsive(
        timeout=50.0, pause=0.1, check=lambda: is_responsive(url)
    )
    return url


@pytest.fixture(scope="session")
def keycloak(keycloak_service):
    return {
        "issuer": f"{keycloak_service}/realms/plone-test",
        "client_id": "plone",
        "client_secret": "12345678",  # nosec B105
        "scope": ("openid", "profile", "email"),
    }


@pytest.fixture
def wait_for():
    def func(thread):
        if not thread:
            return
        thread.join()

    return func
