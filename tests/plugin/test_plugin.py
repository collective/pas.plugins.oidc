from base64 import b64decode
from oic.oic.message import OpenIDSchema
from pas.plugins.oidc import PLUGIN_ID
from plone import api
from plone.session.tktauth import splitTicket

import pytest


class TestPlugin:
    @pytest.fixture(autouse=True)
    def _initialize(self, portal, http_request):
        self.pas = api.portal.get_tool("acl_users")
        self.plugin = getattr(self.pas, PLUGIN_ID)
        self.http_request = http_request
        self.http_response = http_request.response

    @pytest.mark.parametrize(
        "property,expected",
        [
            ("create_user", True),
            ("create_ticket", True),
        ],
    )
    def test_plugin_setup(self, property, expected):
        plugin = self.plugin
        assert plugin.getProperty(property) is expected

    def test_remember_identity(self):
        pas = self.pas
        plugin = self.plugin
        userinfo = OpenIDSchema(sub="bob")
        assert pas.getUserById("bob") is None
        # Remember identity
        plugin.rememberIdentity(userinfo)
        assert pas.getUserById("bob") is not None
        # Response tests
        assert self.http_response.status == 200
        cookie_value = b64decode(self.http_response.cookies["__ac"]["value"])
        assert splitTicket(cookie_value)[1] == "bob"

    def test_challenge(self):
        http_request = self.http_request
        http_response = self.http_response
        plugin = self.plugin
        request_url = http_request.URL
        assert plugin.challenge(http_request, http_response) is True

        # Check the response.
        plugin_url = plugin.absolute_url()
        expected_url = f"{plugin_url}/require_login?came_from={request_url}"
        assert http_response.headers["location"] == expected_url
