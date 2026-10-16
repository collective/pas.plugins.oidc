from plone import api

import pytest


class TestControlPanel:
    url: str = ""

    @pytest.fixture(autouse=True)
    def _initialize(self, browser_manager):
        self.browser = browser_manager
        self.portal_url = api.portal.get().absolute_url()
        self.url = f"{self.portal_url}/@@oidc-controlpanel"

    def test_exists(self):
        browser = self.browser
        browser.open(self.url)
        assert browser.url == self.url
        assert browser.headers["status"] == "200 OK"

    def test_client_secret_is_masked_and_preserved(self, portal):
        browser = self.browser
        browser.open(self.url)

        assert browser.getControl(name="form.widgets.client_secret").value == "********"
        browser.getControl(name="form.widgets.client_secret").value = "foobar"
        browser.getControl(name="form.buttons.save").click()

        assert portal.acl_users.oidc.client_secret == "foobar"  # noqa: S105

        browser.open(self.url)
        assert browser.getControl(name="form.widgets.client_secret").value == "********"
        browser.getControl(name="form.buttons.save").click()
        assert portal.acl_users.oidc.client_secret == "foobar"  # noqa: S105
