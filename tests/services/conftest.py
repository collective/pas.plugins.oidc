from bs4 import BeautifulSoup
from pas.plugins.oidc.plugins import OIDCPlugin
from plone import api
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.restapi.testing import RelativeSession
from urllib.parse import urlparse
from zope.component.hooks import setSite

import pytest
import requests
import transaction


@pytest.fixture(scope="session")
def keycloak(keycloak_service):
    return {
        "issuer": f"{keycloak_service}/realms/plone-test",
        "client_id": "plone",
        "client_secret": "12345678",  # nosec B105
        "scope": ("openid", "profile", "email"),
        "redirect_uris": ("/login_oidc/oidc",),
        "create_restapi_ticket": True,
    }


@pytest.fixture()
def app(restapi):
    return restapi["app"]


@pytest.fixture()
def portal(restapi, keycloak):
    portal = restapi["portal"]
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
def http_request(restapi):
    return restapi["request"]


@pytest.fixture()
def request_api_factory(portal):
    def factory():
        url = portal.absolute_url()
        api_session = RelativeSession(f"{url}/++api++")
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
def keycloak_login():
    def func(url: str):
        session = requests.Session()
        resp = session.get(url)
        soup = BeautifulSoup(resp.content)
        data = {
            "username": TEST_USER_NAME,
            "password": TEST_USER_PASSWORD,
            "credentialId": "",
        }
        next_url = soup.find("form", attrs={"id": "kc-form-login"})["action"]
        resp = session.post(next_url, data=data, allow_redirects=False)
        location = resp.headers["Location"]
        qs = urlparse(location).query
        return qs

    return func


@pytest.fixture()
def google(restapi):
    portal = restapi["portal"]
    setSite(portal)
    with api.env.adopt_roles(["Manager", "Member"]):
        portal.acl_users._setObject("google", OIDCPlugin("google", "Google"))

    transaction.commit()
    yield portal
