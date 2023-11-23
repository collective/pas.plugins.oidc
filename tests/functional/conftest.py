from plone import api
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.testing.zope import Browser
from zope.component.hooks import setSite

import pytest
import transaction


@pytest.fixture()
def app(functional):
    return functional["app"]


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
