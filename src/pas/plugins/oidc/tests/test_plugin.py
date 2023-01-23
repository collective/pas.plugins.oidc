from base64 import b64decode
from oic.oic.message import OpenIDSchema

# from pas.plugins.oidc.tests.mocks import make_user
from pas.plugins.oidc.setuphandlers import post_install
from pas.plugins.oidc.testing import PAS_PLUGINS_OIDC_INTEGRATION_TESTING
from plone.session.tktauth import splitTicket

import unittest


class TestPlugin(unittest.TestCase):

    layer = PAS_PLUGINS_OIDC_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.pas = self.portal.acl_users
        self.plugin = post_install(self.portal)
        self.request = self.layer["request"]
        self.response = self.request.response

    def test_remember_identity(self):
        userinfo = OpenIDSchema(sub="bob")
        # auto create user by default
        self.assertTrue(self.plugin.getProperty("create_user"))
        # set __ac ticket by default
        self.assertTrue(self.plugin.getProperty("create_ticket"))
        self.assertIsNone(self.pas.getUserById("bob"))
        self.plugin.rememberIdentity(userinfo)
        self.assertIsNotNone(self.pas.getUserById("bob"))
        self.assertEqual(self.response.status, 200)
        self.assertEqual(
            splitTicket(b64decode(self.response.cookies["__ac"]["value"]))[1], "bob"
        )

    def test_challenge(self):
        request_url = self.request.URL

        # When the plugin makes a challenge, it must return a True value.
        self.assertTrue(self.plugin.challenge(self.request, self.response))

        # Check the response.
        plugin_url = self.plugin.absolute_url()
        self.assertEqual(
            self.response.headers["location"],
            "{}/require_login?came_from={}".format(plugin_url, request_url),
        )
