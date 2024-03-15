from pas.plugins.oidc import PACKAGE_NAME
from pas.plugins.oidc.plugins import OIDCPlugin
from plone import api

import pytest


class TestSetupInstall:
    @pytest.fixture(autouse=True)
    def _initialize(self, portal, api_anon_request):
        self.portal = portal
        self.api_session = api_anon_request
        self.portal.acl_users._setObject(
            "google", OIDCPlugin(id="google", title="Google")
        )

    def test_login_get_available(self):
        response = self.api_session.get("@login")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.parametrize(
        "idx, key, expected",
        [
            [0, "id", "oidc"],
            [0, "plugin", "oidc"],
            [0, "url", "/@login-oidc/oidc"],
            [0, "title", "OIDC Connect"],
            [0, "id", "google"],
            [0, "plugin", "oidc"],
            [0, "url", "/@login-oidc/google"],
            [0, "title", "Google"],
        ],
    )
    def test_login_get_options(self, idx: int, key: str, expected: str):
        response = self.api_session.get("@login")
        data = response.json()
        options = data["options"]
        assert expected in options[idx][key]
