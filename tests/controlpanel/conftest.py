from plone import api
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.restapi.testing import RelativeSession
from zope.component.hooks import setSite

import pytest
import transaction


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
def api_manager_request(request_api_factory):
    request = request_api_factory()
    request.auth = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)
    yield request
    request.auth = ()
