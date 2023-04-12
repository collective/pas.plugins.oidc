from base64 import b64decode
from oic.oic.message import OpenIDSchema

# from pas.plugins.oidc.tests.mocks import make_user
from pas.plugins.oidc.setuphandlers import post_install
from pas.plugins.oidc.testing import PAS_PLUGINS_OIDC_INTEGRATION_TESTING
from plone.session.tktauth import splitTicket
from plone import api

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

    def test_get_userinfo_base(self):
        userinfo = OpenIDSchema(
            sub="bob", name="Bob", family_name="the Builder", email="bob@example.org"
        )
        self.assertEquals(self.plugin.create_user, True)
        self.plugin.rememberIdentity(userinfo)
        bob = api.user.get(username="bob")
        self.assertEquals(bob.getProperty("fullname"), "Bob the Builder")
        self.assertEquals(bob.getProperty("email"), "bob@example.org")

    def test_get_userinfo_extended(self):
        userinfo = OpenIDSchema(
            sub="bob", name="Bob", family_name="the Builder", email="bob@example.org"
        )
        self.assertEquals(self.plugin.create_user, True)
        self.plugin.userinfo_to_memberdata = (
            "name|first_name",
            "family_name|last_name",
        )
        self.plugin.rememberIdentity(userinfo)
        self.plugin.rememberIdentity(userinfo)
        bob = api.user.get(username="bob")
        self.assertIn(bob.getId(), self.plugin._userdata_by_userid)
        self.assertEquals(bob.getProperty("fullname"), "Bob the Builder")
        self.assertEquals(bob.getProperty("first_name"), "Bob")
        self.assertEquals(bob.getProperty("last_name"), "the Builder")
        self.assertEquals(bob.getProperty("email"), "bob@example.org")

    def test_standard_plone_user(self):
        test_user = api.user.get_current()
        test_user.setProperties(fullname="Test User")
        self.assertNotIn(test_user.getId(), self.plugin._userdata_by_userid)
        self.assertEquals(test_user.getProperty("fullname"), "Test User")

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
