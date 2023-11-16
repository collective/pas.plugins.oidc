from pas.plugins.oidc import utils

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
