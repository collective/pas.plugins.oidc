from pas.plugins.oidc import utils
from pas.plugins.oidc.session import Session

import os
import pytest


class TestUtilsFlowStart:
    @pytest.fixture(autouse=True)
    def _initialize(self, portal, http_request):
        self.portal = portal
        self.http_request = http_request
        self.plugin = utils.get_plugins()[0]

    @pytest.fixture()
    def session_factory(self):
        def func():
            return utils.initialize_session(self.plugin, self.http_request)

        return func

    def test_initialize_session_default(self):
        func = utils.initialize_session
        session = func(self.plugin, self.http_request)
        assert isinstance(session, Session)
        assert isinstance(session.get("state"), str)
        assert isinstance(session.get("nonce"), str)
        # No came_from in the request
        assert session.get("came_from") is None
        # By default we do not use pkce
        assert session.get("verifier") is None

    def test_initialize_session_came_from(self):
        func = utils.initialize_session
        came_from = f"{self.portal.absolute_url()}/a-page"
        self.http_request.set("came_from", came_from)
        session = func(self.plugin, self.http_request)
        assert session.get("came_from") == came_from

    def test_initialize_session_verifier(self):
        func = utils.initialize_session
        self.plugin.use_pkce = True
        session = func(self.plugin, self.http_request)
        assert isinstance(session.get("verifier"), str)

    def test_pkce_code_verifier_challenge(self):
        func = utils.pkce_code_verifier_challenge
        value = str(os.urandom(40))
        result = func(value)
        assert isinstance(result, str)
        assert "=" not in result

    def test_authorization_flow_args(self, session_factory):
        func = utils.authorization_flow_args
        result = func(self.plugin, session_factory())
        assert isinstance(result, dict)
        assert result["client_id"] == self.plugin.client_id
        assert result["response_type"] == "code"
        assert result["scope"] == ["profile", "email", "phone"]
        assert isinstance(result["state"], str)
        assert isinstance(result["nonce"], str)
        assert "code_challenge" not in result
        assert "code_challenge_method" not in result

    def test_authorization_flow_args_pkce(self, session_factory):
        self.plugin.use_pkce = True
        func = utils.authorization_flow_args
        result = func(self.plugin, session_factory())
        assert isinstance(result["code_challenge"], str)
        assert isinstance(result["code_challenge_method"], str)
