from pas.plugins.oidc.testing import PAS_PLUGINS_OIDC_FUNCTIONAL_TESTING
from plone.testing.zope import Browser
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD

import unittest

try:
    # Python 3
    from urllib.parse import quote
except ImportError:
    # Python 2
    from urllib import quote


class TestFunctionalPlugin(unittest.TestCase):

    layer = PAS_PLUGINS_OIDC_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False

    def test_challenge_anonymous(self):
        self.browser.handleErrors = True
        # self.browser.raiseHttpErrors = False
        self.browser.followRedirects = False
        portal_url = self.portal.absolute_url()
        plugin_url = self.portal.acl_users.oidc.absolute_url()

        # Try going to a page for which you need to be authenticated.
        url = portal_url + "/@@overview-controlpanel"
        quoted_url = quote(url)
        self.browser.open(url)

        # Since we have told the browser to not follow redirects,
        # we are at the requested location.
        self.assertEqual(self.browser.url, url)
        # Plone wants to redirect us to the require_login page of the plugin.
        location = self.browser.headers["location"]
        self.assertEqual(location, plugin_url + "/require_login?came_from=" + url)

        # Follow one redirect.
        self.browser.open(location)
        self.assertEqual(self.browser.url, location)
        # Plone wants to redirect us to the login page of the plugin.
        location = self.browser.headers["location"]
        self.assertEqual(location, plugin_url + "/login?came_from=" + quoted_url)

        # If we would follow the redirect, we would get a 500 Internal Server Error
        # because the login view calls get_oauth2_client on the plugin,
        # and we have not setup such a client in the tests.  We may need to mock
        # some code.
        # But the challenge plugin works: it makes sure we end up on the login view
        # of our plugin, and not on the standard Plone login form.

    def test_challenge_authenticated_manager(self):
        self.browser.addHeader(
            "Authorization",
            "Basic {0}:{1}".format(
                SITE_OWNER_NAME,
                SITE_OWNER_PASSWORD,
            ),
        )
        self.browser.handleErrors = True
        # self.browser.raiseHttpErrors = False
        self.browser.followRedirects = False
        portal_url = self.portal.absolute_url()
        plugin_url = self.portal.acl_users.oidc.absolute_url()

        # Try going to a page for which you need to be authenticated.
        url = portal_url + "/@@overview-controlpanel"
        self.browser.open(url)

        # we are at the requested location.
        self.assertEqual(self.browser.url, url)
        self.assertEqual(self.browser.headers["status"], "200 OK")
        self.assertIn("Site Setup", self.browser.contents)
        self.assertIn("Log out", self.browser.contents)

    def test_challenge_authenticated_member(self):
        self.browser.addHeader(
            "Authorization",
            "Basic {0}:{1}".format(
                TEST_USER_NAME,
                TEST_USER_PASSWORD,
            ),
        )
        self.browser.handleErrors = True
        # self.browser.raiseHttpErrors = False
        self.browser.followRedirects = False
        portal_url = self.portal.absolute_url()
        plugin_url = self.portal.acl_users.oidc.absolute_url()

        # Try going to a page for which you need to be authenticated.
        url = portal_url + "/@@overview-controlpanel"
        quoted_url = quote(url)
        self.browser.open(url)

        # Since we have told the browser to not follow redirects,
        # we are at the requested location.
        self.assertEqual(self.browser.url, url)
        # Plone wants to redirect us to the require_login page of the plugin.
        location = self.browser.headers["location"]
        self.assertEqual(location, plugin_url + "/require_login?came_from=" + url)

        # Follow one redirect.
        self.browser.open(location)
        self.assertEqual(self.browser.url, location)
        # Plone sees that we are authenticated, but do not have sufficient privileges.
        # The plugin does not redirect to the oidc server, because that would likely
        # result in login loops.
        location = self.browser.headers["location"]
        self.assertEqual(location, portal_url + "/insufficient-privileges")
