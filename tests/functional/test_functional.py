from pas.plugins.oidc import PLUGIN_ID
from plone import api
from urllib.parse import quote

import pytest


class TestFunctionalPlugin:
    @pytest.fixture(autouse=True)
    def _initialize(self, portal):
        pas = api.portal.get_tool("acl_users")
        plugin = getattr(pas, PLUGIN_ID)
        self.portal_url = api.portal.get().absolute_url()
        self.plugin_url = plugin.absolute_url()

    def test_challenge_anonymous(self, browser_anonymous):
        browser = browser_anonymous
        browser.handleErrors = True
        url = f"{self.portal_url}/@@overview-controlpanel"
        quoted_url = quote(url)
        browser.open(url)
        # Since we have told the browser to not follow redirects,
        # we are at the requested location.
        assert browser.url == url
        # Plone wants to redirect us to the require_login page of the plugin.
        location = browser.headers["location"]
        expected = f"{self.plugin_url}/require_login?came_from={url}"
        assert location == expected

        # Follow one redirect.
        browser.open(location)
        assert browser.url == location
        # Plone wants to redirect us to the login page of the plugin.
        location = browser.headers["location"]
        expected = f"{self.plugin_url}/login?came_from={quoted_url}"
        assert location == expected
        # Follow one redirect, view the login page of the plugin
        browser.handleErrors = False
        browser.open(location)
        assert browser.url == location
        # The next redirect will send us to keycloak
        location = browser.headers["location"]
        expected = "http://127.0.0.1:8180/realms/plone-test/protocol/openid-connect/auth?client_id=plone"
        assert location.startswith(expected)

    def test_challenge_authenticated_user(self, browser_user):
        browser = browser_user
        browser.handleErrors = True
        url = f"{self.portal_url}/@@overview-controlpanel"
        browser.open(url)
        # Since we have told the browser to not follow redirects,
        # we are at the requested location.
        assert browser.url == url
        # Plone wants to redirect us to the require_login page of the plugin.
        location = browser.headers["location"]
        expected = f"{self.plugin_url}/require_login?came_from={url}"
        assert location == expected

        # Follow one redirect.
        browser.open(location)
        assert browser.url == location
        # Plone sees that we are authenticated, but do not have sufficient privileges.
        # The plugin does not redirect to the oidc server, because that would likely
        # result in login loops.
        location = browser.headers["location"]
        expected = f"{self.portal_url}/insufficient-privileges"
        assert location == expected

    def test_challenge_authenticated_manager(self, browser_manager):
        browser = browser_manager
        browser.handleErrors = True
        portal_url = self.portal_url
        # Try going to a page for which you need to be authenticated.
        url = f"{portal_url}/@@overview-controlpanel"
        browser.open(url)
        assert browser.url == url
        assert browser.headers["status"] == "200 OK"
        assert "Site Setup" in browser.contents
        assert "Log out" in browser.contents
