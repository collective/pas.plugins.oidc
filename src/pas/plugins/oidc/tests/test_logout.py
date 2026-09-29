from types import SimpleNamespace
from unittest import TestCase

from pas.plugins.oidc.browser.view import revoke_restapi_token


class LogoutTokenRevocationTest(TestCase):
    def make_pas(self, tokens, payload=None, decode_error=None):
        def decode_token(token):
            if decode_error is not None:
                raise decode_error
            return payload or {"sub": "alice"}

        jwt_auth = SimpleNamespace(
            _decode_token=decode_token,
            _tokens=tokens,
        )
        return {"jwt_auth": jwt_auth}

    def test_revokes_only_presented_token(self):
        tokens = {
            "alice": {"presented": None, "other-session": None},
            "bob": {"bob-session": None},
        }

        revoked = revoke_restapi_token(self.make_pas(tokens), "presented")

        self.assertTrue(revoked)
        self.assertEqual(tokens["alice"], {"other-session": None})
        self.assertEqual(tokens["bob"], {"bob-session": None})

    def test_missing_cookie_is_safe_noop(self):
        tokens = {"alice": {"presented": None}}

        revoked = revoke_restapi_token(self.make_pas(tokens), None)

        self.assertFalse(revoked)
        self.assertIn("presented", tokens["alice"])

    def test_invalid_token_is_safe_noop(self):
        tokens = {"alice": {"presented": None}}
        pas = self.make_pas(tokens, decode_error=ValueError("invalid token"))

        revoked = revoke_restapi_token(pas, "presented")

        self.assertFalse(revoked)
        self.assertIn("presented", tokens["alice"])

    def test_undecodable_token_is_safe_noop(self):
        tokens = {"alice": {"presented": None}}
        pas = self.make_pas(tokens, payload=["invalid payload"])

        revoked = revoke_restapi_token(pas, "presented")

        self.assertFalse(revoked)
        self.assertIn("presented", tokens["alice"])

    def test_unstored_token_is_safe_noop(self):
        tokens = {"alice": {"other-session": None}}

        revoked = revoke_restapi_token(self.make_pas(tokens), "presented")

        self.assertFalse(revoked)
        self.assertEqual(tokens["alice"], {"other-session": None})
