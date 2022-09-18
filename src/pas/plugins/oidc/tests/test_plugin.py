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
        self.assertTrue(self.plugin.create_user)
        # set __ac ticket by default
        self.assertTrue(self.plugin.create_ticket)
        self.assertIsNone(self.pas.getUserById("bob"))
        self.plugin.rememberIdentity(userinfo)
        self.assertIsNotNone(self.pas.getUserById("bob"))
        self.assertEqual(self.response.status, 200)
        self.assertEqual(
            splitTicket(b64decode(self.response.cookies["__ac"]["value"]))[1], "bob"
        )
