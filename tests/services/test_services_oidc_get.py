from pas.plugins.oidc import PACKAGE_NAME
from urllib.parse import parse_qsl
from urllib.parse import urlparse

import pytest
import transaction


class TestServiceOIDCGet:
    endpoint: str = "@login-oidc/oidc"

    @pytest.fixture(autouse=True)
    def _initialize(self, api_anon_request):
        self.api_session = api_anon_request

    def test_login_oidc_get_available(self):
        response = self.api_session.get(self.endpoint)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.parametrize(
        "key",
        [
            "came_from",
            "next_url",
        ],
    )
    def test_login_oidc_response_keys(self, key: str):
        response = self.api_session.get(self.endpoint)
        data = response.json()
        assert key in data

    def test_login_oidc_next_url(self):
        response = self.api_session.get(self.endpoint)
        data = response.json()
        next_url = data["next_url"]
        url_parts = urlparse(next_url)
        assert url_parts.netloc == "127.0.0.1:8180"
        qs = dict(parse_qsl(url_parts.query))
        assert qs["client_id"] == "plone"
        assert qs["response_type"] == "code"
        assert qs["scope"] == "openid profile email"
        assert qs["redirect_uri"].endswith("/plone/login_oidc/oidc")
        assert "state" in qs
        assert "nonce" in qs

    def test_login_oidc_allowed_idp_hint(self, portal):
        plugin = portal.acl_users.oidc
        plugin.idp_hint_query_key = "kc_idp_hint"
        plugin.idp_hint_allowed_values = ("foo",)
        transaction.commit()

        response = self.api_session.get(f"{self.endpoint}?kc_idp_hint=foo")
        next_url = response.json()["next_url"]
        qs = dict(parse_qsl(urlparse(next_url).query))

        assert qs["kc_idp_hint"] == "foo"

    def test_login_oidc_rejects_unallowed_idp_hint(self, portal):
        plugin = portal.acl_users.oidc
        plugin.idp_hint_query_key = "kc_idp_hint"
        plugin.idp_hint_allowed_values = ("foo",)
        transaction.commit()

        response = self.api_session.get(f"{self.endpoint}?kc_idp_hint=bar")
        qs = dict(parse_qsl(urlparse(response.json()["next_url"]).query))

        assert "kc_idp_hint" not in qs


class TestServiceOIDCGetFailure:
    endpoint: str = "@login-oidc/oidc"

    @pytest.fixture(autouse=True)
    def _initialize(self, api_anon_request, installer):
        installer.uninstall_product(PACKAGE_NAME)
        self.api_session = api_anon_request
        transaction.commit()

    def test_login_oidc_not_found(self):
        response = self.api_session.get(self.endpoint)
        assert response.status_code == 404
        data = response.json()
        assert isinstance(data, dict)


class TestServiceOIDCLogout:
    endpoint: str = "@logout-oidc"

    @pytest.fixture(autouse=True)
    def _initialize(self, api_anon_request, keycloak_login):
        login_endpoint = "@login-oidc/oidc"
        self.api_session = api_anon_request
        response = self.api_session.get(login_endpoint)
        data = response.json()
        next_url = data["next_url"]
        qs = keycloak_login(next_url)
        self.api_session.post(login_endpoint, json={"qs": qs})

    def test_logout(self):
        response = self.api_session.get(self.endpoint)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
