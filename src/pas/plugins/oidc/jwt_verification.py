"""
JWT verification using cryptojwt with proper secp256k1 (P-256K) support.

This module provides an alternative to pyjwkest for verifying EU Login
ID tokens signed with the secp256k1 elliptic curve.
"""

import base64
import copy
import json
import logging
import time

import requests

logger = logging.getLogger(__name__)

# EU Login JWKS uses "secp256k1" but cryptojwt expects "P-256K"
CURVE_ALIASES = {
    "secp256k1": "P-256K",
}

# Algorithm to set on keys when normalizing secp256k1 curves
CURVE_ALG = {
    "secp256k1": "ES256K",
}

# Simple JWKS cache: {uri: (jwks_dict, timestamp)}
_jwks_cache = {}
_CACHE_TTL = 300  # 5 minutes
_DEFAULT_ALLOWED_ALGS = ("ES256K",)
_DEFAULT_CLOCK_SKEW_SECONDS = 120


class TokenValidationError(Exception):
    """Raised when a token fails security validation."""


class CompatibilityVerificationError(Exception):
    """Raised for technical issues where pyjwkest fallback is acceptable."""


def normalize_jwks_curves(jwks_dict):
    """Rewrite curve names in a JWKS dict so cryptojwt can parse them.

    EU Login publishes JWKS with "crv": "secp256k1", but cryptojwt
    expects "P-256K". Also sets the correct algorithm on the key.
    """
    normalized = copy.deepcopy(jwks_dict)
    for key in normalized.get("keys", []):
        crv = key.get("crv", "")
        if crv in CURVE_ALIASES:
            key["crv"] = CURVE_ALIASES[crv]
            key["alg"] = CURVE_ALG[crv]
    return normalized


def fetch_jwks(jwks_uri):
    """Fetch JWKS from the provider, with simple TTL caching."""
    now = time.time()
    cached = _jwks_cache.get(jwks_uri)
    if cached and (now - cached[1]) < _CACHE_TTL:
        return cached[0]

    resp = requests.get(jwks_uri, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    _jwks_cache[jwks_uri] = (data, now)
    return data


def _decode_segment(segment):
    """Decode a base64url segment from a compact JWT."""
    if not isinstance(segment, str):
        raise TokenValidationError("JWT segment must be text")
    padded = segment + ("=" * ((4 - len(segment) % 4) % 4))
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception as exc:
        raise TokenValidationError(
            "Failed to decode JWT segment"
        ) from exc


def _decode_header(id_token_jwt):
    """Decode JWT header without trusting its claims."""
    parts = id_token_jwt.split(".")
    if len(parts) != 3:
        raise TokenValidationError("Invalid compact JWT format")
    try:
        return json.loads(_decode_segment(parts[0]).decode("utf-8"))
    except Exception as exc:
        raise TokenValidationError("Invalid JWT header JSON") from exc


def _decode_verified_payload(payload):
    """Convert a verified payload from cryptojwt/pyjwkest into a dict."""
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception as exc:
            raise TokenValidationError("JWT payload is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise TokenValidationError(
            "JWT payload has invalid type: %s" % type(payload).__name__
        )
    return payload


def _as_int(claim_name, value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TokenValidationError(
            "Claim %s must be an integer timestamp" % claim_name
        ) from exc


def _validate_claims(
    claims,
    issuer=None,
    client_id=None,
    nonce=None,
    leeway=_DEFAULT_CLOCK_SKEW_SECONDS,
):
    """Validate OIDC ID token claims required by this plugin."""
    if not isinstance(claims, dict):
        raise TokenValidationError("Claims must be a dict")

    if not claims.get("sub"):
        raise TokenValidationError("Missing required claim: sub")

    if issuer and claims.get("iss") != issuer:
        raise TokenValidationError(
            "Invalid issuer: expected %s, got %s"
            % (issuer, claims.get("iss"))
        )

    aud = claims.get("aud")
    if client_id:
        if isinstance(aud, list):
            if client_id not in aud:
                raise TokenValidationError(
                    "Invalid audience: %s not in %s" % (client_id, aud)
                )
            # OIDC: azp is required if multiple audiences are present.
            if len(aud) > 1 and claims.get("azp") != client_id:
                raise TokenValidationError(
                    "Invalid azp: expected %s, got %s"
                    % (client_id, claims.get("azp"))
                )
        elif isinstance(aud, str):
            if aud != client_id:
                raise TokenValidationError(
                    "Invalid audience: expected %s, got %s"
                    % (client_id, aud)
                )
        else:
            raise TokenValidationError("Invalid audience claim type")

    if nonce and claims.get("nonce") != nonce:
        raise TokenValidationError("Invalid nonce")

    now = int(time.time())
    exp = _as_int("exp", claims.get("exp"))
    nbf = _as_int("nbf", claims.get("nbf"))
    iat = _as_int("iat", claims.get("iat"))

    if exp is not None and now > (exp + leeway):
        raise TokenValidationError("Token has expired")

    if nbf is not None and now + leeway < nbf:
        raise TokenValidationError("Token is not yet valid (nbf)")

    # Protect against tokens that claim to be minted too far in the future.
    if iat is not None and iat > (now + leeway):
        raise TokenValidationError("Token issued-at time is in the future")


def _normalize_allowed_algs(allowed_algs):
    if allowed_algs is None:
        return set(_DEFAULT_ALLOWED_ALGS)
    if isinstance(allowed_algs, str):
        return {allowed_algs}
    return set(allowed_algs)


def verify_id_token(
    id_token_jwt,
    jwks_uri,
    issuer=None,
    client_id=None,
    nonce=None,
    allowed_algs=None,
    leeway=_DEFAULT_CLOCK_SKEW_SECONDS,
):
    """Verify an ID token JWT using cryptojwt with secp256k1 support.

    Args:
        id_token_jwt: Raw JWT string (header.payload.signature)
        jwks_uri: URL of the OIDC provider's JWKS endpoint
        issuer: Expected issuer claim (optional validation)
        client_id: Expected audience claim (optional validation)
        nonce: Expected nonce claim from the login session
        allowed_algs: Iterable of accepted signing algorithms
        leeway: Clock skew in seconds for time-based claims

    Returns:
        dict: Verified JWT claims

    Raises:
        TokenValidationError: If token is invalid
        CompatibilityVerificationError: If cryptojwt cannot process keys
    """
    header = _decode_header(id_token_jwt)
    alg = header.get("alg")
    if not alg:
        raise TokenValidationError("Missing JWT header alg")

    allowed_alg_set = _normalize_allowed_algs(allowed_algs)
    if alg not in allowed_alg_set:
        raise TokenValidationError(
            "Unexpected JWT alg: %s (allowed: %s)"
            % (alg, ", ".join(sorted(allowed_alg_set)))
        )

    # Fetch and normalize JWKS
    jwks = fetch_jwks(jwks_uri)
    jwks_normalized = normalize_jwks_curves(jwks)

    # Load keys
    try:
        from cryptojwt.key_bundle import KeyBundle
    except Exception as exc:
        raise CompatibilityVerificationError(
            "cryptojwt import failure"
        ) from exc

    try:
        kb = KeyBundle(jwks_normalized["keys"])
        keys = kb.keys()
    except Exception as exc:
        raise CompatibilityVerificationError(
            "Unable to load keys in cryptojwt"
        ) from exc

    if not keys:
        raise CompatibilityVerificationError("No keys loaded from JWKS")

    # Verify JWT signature
    try:
        from cryptojwt.jws.jws import JWS

        verifier = JWS(alg=alg)
        payload = verifier.verify_compact(id_token_jwt, keys, sigalg=alg)
    except Exception as exc:
        raise TokenValidationError(
            "ID token signature verification failed"
        ) from exc

    claims = _decode_verified_payload(payload)
    _validate_claims(
        claims,
        issuer=issuer,
        client_id=client_id,
        nonce=nonce,
        leeway=leeway,
    )
    return claims


def do_token_exchange(
    token_endpoint, code, redirect_uris, client_id, client_secret,
    code_verifier=None,
):
    """Exchange an authorization code for tokens via HTTP POST.

    Args:
        token_endpoint: URL of the token endpoint
        code: Authorization code from the callback
        redirect_uris: List of redirect URIs (first one is used)
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        code_verifier: PKCE code verifier (optional)

    Returns:
        dict: Raw token response containing access_token, id_token, etc.
    """
    redirect_uri = redirect_uris[0] if isinstance(redirect_uris, list) else redirect_uris

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    if code_verifier:
        data["code_verifier"] = code_verifier

    resp = requests.post(
        token_endpoint,
        data=data,
        auth=(client_id, client_secret),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def verify_id_token_pyjwkest(
    id_token_jwt,
    jwks_uri,
    issuer=None,
    client_id=None,
    nonce=None,
    allowed_algs=None,
    leeway=_DEFAULT_CLOCK_SKEW_SECONDS,
):
    """Verify ID token with pyjwkest, then apply strict claim validation."""
    header = _decode_header(id_token_jwt)
    alg = header.get("alg")
    if not alg:
        raise TokenValidationError("Missing JWT header alg")

    allowed_alg_set = _normalize_allowed_algs(allowed_algs)
    if alg not in allowed_alg_set:
        raise TokenValidationError(
            "Unexpected JWT alg: %s (allowed: %s)"
            % (alg, ", ".join(sorted(allowed_alg_set)))
        )

    from jwkest.jws import JWS as JWS_pyjwkest
    from jwkest.jwk import KEYS

    jwks = fetch_jwks(jwks_uri)
    keys = KEYS()
    try:
        keys.load_jwks(json.dumps(jwks))
    except Exception as exc:
        raise CompatibilityVerificationError(
            "Unable to load keys in pyjwkest"
        ) from exc

    try:
        verifier = JWS_pyjwkest()
        payload = verifier.verify_compact(id_token_jwt, keys)
    except Exception as exc:
        raise TokenValidationError(
            "ID token signature verification failed in pyjwkest fallback"
        ) from exc

    claims = _decode_verified_payload(payload)
    _validate_claims(
        claims,
        issuer=issuer,
        client_id=client_id,
        nonce=nonce,
        leeway=leeway,
    )
    return claims
