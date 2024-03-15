import pytest


class TestServiceLoginGet:
    @pytest.fixture(autouse=True)
    def _initialize(self, api_anon_request):
        self.api_session = api_anon_request

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
            [0, "title", "OpenID Connect"],
        ],
    )
    def test_login_get_options(self, idx: int, key: str, expected: str):
        response = self.api_session.get("@login")
        data = response.json()
        options = data["options"]
        assert expected in options[idx][key]
