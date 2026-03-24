from Products.Five.browser import BrowserView
import traceback


class TestJWTView(BrowserView):
    """Diagnostic view to test cryptojwt availability and EU Login key loading.

    Access: @@test-jwt (requires Manager role)
    Safe: read-only, no login flow changes, only fetches public keys.
    Remove after testing is complete.
    """

    def __call__(self):
        self.request.response.setHeader("Content-Type", "text/plain")
        output = []

        # --- Test 1: Can we import cryptojwt? ---
        output.append("=== Test 1: Import cryptojwt ===")
        try:
            from cryptojwt.jws.jws import JWS  # noqa: F401
            from cryptojwt.key_bundle import KeyBundle  # noqa: F401

            output.append("PASS - cryptojwt is installed and importable")
        except Exception:
            output.append("FAIL")
            output.append(traceback.format_exc())
            return "\n".join(output)

        output.append("")

        # --- Test 2: Can cryptojwt handle a secp256k1 (P-256K) key? ---
        output.append("=== Test 2: Load a P-256K key into cryptojwt ===")
        try:
            # A hardcoded test key (not a real key, just valid EC points)
            from cryptography.hazmat.primitives.asymmetric import ec
            import base64

            # Generate a throwaway secp256k1 key pair
            private_key = ec.generate_private_key(ec.SECP256K1())
            numbers = private_key.public_key().public_numbers()

            def int_to_b64url(n, length):
                return base64.urlsafe_b64encode(
                    n.to_bytes(length, "big")
                ).rstrip(b"=").decode()

            test_jwk = {
                "kty": "EC",
                "crv": "P-256K",
                "alg": "ES256K",
                "x": int_to_b64url(numbers.x, 32),
                "y": int_to_b64url(numbers.y, 32),
            }

            kb = KeyBundle([test_jwk])
            keys = kb.keys()
            output.append(
                "PASS - loaded %d key(s) with P-256K curve" % len(keys)
            )
        except Exception:
            output.append("FAIL")
            output.append(traceback.format_exc())
            return "\n".join(output)

        output.append("")

        # --- Test 3: Can cryptojwt load EU Login's real JWKS? ---
        output.append("=== Test 3: Fetch and load EU Login JWKS ===")
        try:
            from Products.CMFCore.utils import getToolByName
            from pas.plugins.oidc.jwt_verification import (
                fetch_jwks,
                normalize_jwks_curves,
            )

            pas = getToolByName(self.context, "acl_users")

            # Find the OIDC plugin
            plugin = None
            for p_id, p in pas.objectItems():
                if hasattr(p, "get_oauth2_client"):
                    plugin = p
                    break

            if not plugin:
                output.append("SKIP - no OIDC plugin found in acl_users")
                return "\n".join(output)

            client = plugin.get_oauth2_client()
            jwks_uri = client.provider_info["jwks_uri"]
            output.append("JWKS URI: %s" % jwks_uri)

            # Fetch
            raw_jwks = fetch_jwks(jwks_uri)
            output.append("Keys found: %d" % len(raw_jwks.get("keys", [])))
            for k in raw_jwks.get("keys", []):
                output.append(
                    "  - kid=%s  crv=%s  kty=%s"
                    % (k.get("kid", "?"), k.get("crv", "?"), k.get("kty", "?"))
                )

            # Normalize and load
            normalized = normalize_jwks_curves(raw_jwks)
            kb2 = KeyBundle(normalized["keys"])
            loaded = kb2.keys()
            output.append("")
            output.append(
                "PASS - cryptojwt loaded %d key(s) from EU Login" % len(loaded)
            )
        except Exception:
            output.append("FAIL")
            output.append(traceback.format_exc())

        return "\n".join(output)
