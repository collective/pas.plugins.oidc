from plone import api
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.restapi.testing import RelativeSession
from plone.testing.zope import Browser
from requests.exceptions import ConnectionError
from zope.component.hooks import setSite

import pytest
import requests
import transaction


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
        timeout=30.0, pause=0.1, check=lambda: is_responsive(url)
    )
    return url


@pytest.fixture()
def app(functional):
    return functional["app"]


@pytest.fixture(scope="session")
def keycloak(keycloak_service):
    return {
        "issuer": f"{keycloak_service}/realms/plone-test",
        "client_id": "plone",
        "client_secret": "12345678",  # nosec B105
        "scope": ("openid", "profile", "email"),
    }


@pytest.fixture()
def portal(functional, keycloak):
    portal = functional["portal"]
    setSite(portal)
    plugin = portal.acl_users.oidc
    with api.env.adopt_roles(["Manager", "Member"]):
        for key, value in keycloak.items():
            setattr(plugin, key, value)
    transaction.commit()
    yield portal
    with api.env.adopt_roles(["Manager", "Member"]):
        for key, value in keycloak.items():
            if key != "scope":
                value = ""
            setattr(plugin, key, value)
    transaction.commit()


@pytest.fixture()
def http_request(functional):
    return functional["request"]


@pytest.fixture()
def request_api_factory(portal):
    def factory():
        url = portal.absolute_url()
        api_session = RelativeSession(url)
        api_session.headers.update({"Accept": "application/json"})
        return api_session

    return factory


@pytest.fixture()
def api_anon_request(request_api_factory):
    return request_api_factory()


@pytest.fixture()
def api_user_request(request_api_factory):
    request = request_api_factory()
    request.auth = (TEST_USER_NAME, TEST_USER_PASSWORD)
    yield request
    request.auth = ()


@pytest.fixture()
def api_manager_request(request_api_factory):
    request = request_api_factory()
    request.auth = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
    yield request
    request.auth = ()


@pytest.fixture()
def browser_factory(app):
    def factory():
        browser = Browser(app)
        browser.handleErrors = False
        browser.followRedirects = False
        return browser

    return factory


@pytest.fixture()
def browser_anonymous(browser_factory):
    browser = browser_factory()
    return browser


@pytest.fixture()
def browser_user(browser_factory):
    browser = browser_factory()
    browser.addHeader("Authorization", f"Basic {TEST_USER_NAME}:{TEST_USER_PASSWORD}")
    return browser


@pytest.fixture()
def browser_manager(browser_factory):
    browser = browser_factory()
    browser.addHeader("Authorization", f"Basic {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}")
    return browser
