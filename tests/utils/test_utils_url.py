from pas.plugins.oidc import utils
from plone import api

import pytest


class TestUtilsURL:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("http://plone.org/foo/bar", "http://plone.org/foo/bar"),
            ("http://plone.org/++api++", "http://plone.org"),
            (
                "http://plone.org/++api++/login-oidc/oidc",
                "http://plone.org/login-oidc/oidc",
            ),
            ("http://plone.org/api", "http://plone.org"),
            (
                "http://plone.org/api/login-oidc/oidc",
                "http://plone.org/login-oidc/oidc",
            ),
        ],
    )
    def test_url_cleanup(self, url, expected):
        func = utils.url_cleanup
        assert func(url) == expected


class TestUtilsProcessCameFrom:
    @pytest.fixture(autouse=True)
    def _initialize(self, portal):
        from pas.plugins.oidc.session import Session

        request = api.env.getRequest()
        session = Session(request, False)
        session.set("came_from", f"{portal.absolute_url()}/a-page")
        self.portal = portal
        self.session = session

    def test_process_came_from_session(self):
        func = utils.process_came_from
        assert func(self.session) == f"{self.portal.absolute_url()}/a-page"

    def test_process_came_from_param(self):
        func = utils.process_came_from
        came_from = f"{self.portal.absolute_url()}/a-file"
        assert func(self.session, came_from) == came_from

    def test_process_came_from_param_with_external_url(self):
        func = utils.process_came_from
        portal_url = self.portal.absolute_url()
        came_from = "https://plone.org/"
        assert func(self.session, came_from) == portal_url
