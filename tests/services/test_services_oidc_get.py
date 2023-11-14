from urllib.parse import parse_qsl
from urllib.parse import urlparse

import pytest


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
