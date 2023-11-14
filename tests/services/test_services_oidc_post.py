from plone import api

import pytest


@pytest.fixture()
def wrong_url():
    def func(url: str):
        url = url.replace("localhost", "wrong.localhost")
        return url

    return func


class TestServiceOIDCPost:
    endpoint: str = "@login-oidc/oidc"

    @pytest.fixture(autouse=True)
    def _initialize(self, api_anon_request):
        self.api_session = api_anon_request

    def test_login_oidc_post_wrong_traverse(self):
        """Pointing to a wrong traversal should raise a 404."""
        url = f"{self.endpoint}-wrong"
        response = self.api_session.post(url, json={"qs": "foo=bar"})
        assert response.status_code == 404
        data = response.json()
        assert isinstance(data, dict)
        assert data["error"]["type"] == "Provider not found"
        assert data["error"]["message"] == "Provider oidc-wrong is not available."

    def test_login_oidc_post_success(self, keycloak_login):
        """We need to follow the whole flow."""
        # First get the response from out GET endpoint
        response = self.api_session.get(self.endpoint)
        data = response.json()
        next_url = data["next_url"]
        # Authenticate on keycloak with the url generated by
        # the GET endpoint
        qs = keycloak_login(next_url)
        # Now we do a POST request to our endpoint, passing the
        # returned querystring in the payload
        response = self.api_session.post(self.endpoint, json={"qs": qs})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert data["next_url"] == api.portal.get().absolute_url()
        assert "token" in data

    def test_login_oidc_post_failure(self, keycloak_login, wrong_url):
        """Invalid data on the flow could lead to errors."""
        response = self.api_session.get(self.endpoint)
        data = response.json()
        # Modifying the return url will break the flow
        next_url = wrong_url(data["next_url"])
        qs = keycloak_login(next_url)
        # Now we do a POST request to our endpoint, passing the
        # returned querystring in the payload
        response = self.api_session.post(self.endpoint, json={"qs": qs})
        assert response.status_code == 401
        data = response.json()
        assert isinstance(data, dict)
        assert data["error"]["type"] == "Authentication Error"
        assert data["error"]["message"] == "There was an issue authenticating this user"
