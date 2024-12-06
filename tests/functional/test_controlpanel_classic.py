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
        self.browser.open(self.url)
        assert browser.url == self.url
        assert browser.headers["status"] == "200 OK"
