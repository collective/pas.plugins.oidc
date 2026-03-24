"""
JWT verification using cryptojwt with proper secp256k1 (P-256K) support.

This module provides an alternative to pyjwkest for verifying EU Login
ID tokens signed with the secp256k1 elliptic curve.
"""

import copy
import json
import logging
import time

import requests
from cryptojwt.jws.jws import JWS
from cryptojwt.key_bundle import KeyBundle

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


def verify_id_token(id_token_jwt, jwks_uri, issuer=None, client_id=None):
    """Verify an ID token JWT using cryptojwt with secp256k1 support.

    Args:
        id_token_jwt: Raw JWT string (header.payload.signature)
        jwks_uri: URL of the OIDC provider's JWKS endpoint
        issuer: Expected issuer claim (optional validation)
        client_id: Expected audience claim (optional validation)

    Returns:
        dict: Verified JWT claims

    Raises:
        Exception: If verification fails
    """
    # Fetch and normalize JWKS
    jwks = fetch_jwks(jwks_uri)
    jwks_normalized = normalize_jwks_curves(jwks)

    # Load keys
    kb = KeyBundle(jwks_normalized["keys"])
    keys = kb.keys()

    if not keys:
        raise ValueError("No keys loaded from JWKS")

    # Verify JWT signature
    verifier = JWS()
    verifier["alg"] = "ES256K"
    claims = verifier.verify_compact(id_token_jwt, keys, sigalg="ES256K")

    # Validate claims
    if issuer and claims.get("iss") != issuer:
        raise ValueError(
            "Invalid issuer: expected %s, got %s"
            % (issuer, claims.get("iss"))
        )

    if client_id and claims.get("aud") != client_id:
        aud = claims.get("aud")
        # aud can be a string or a list
        if isinstance(aud, list) and client_id not in aud:
            raise ValueError(
                "Invalid audience: %s not in %s" % (client_id, aud)
            )
        elif isinstance(aud, str) and aud != client_id:
            raise ValueError(
                "Invalid audience: expected %s, got %s" % (client_id, aud)
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