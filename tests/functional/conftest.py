from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.restapi.testing import RelativeSession
from plone.testing.zope import Browser

import pytest


@pytest.fixture()
def app(functional):
    return functional["app"]


@pytest.fixture()
def portal(functional):
    portal = functional["portal"]
    return portal


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
