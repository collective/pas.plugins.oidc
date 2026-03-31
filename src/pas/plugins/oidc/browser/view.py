from hashlib import sha256
from oic import rndstr
from oic.oic.message import AccessTokenResponse
from oic.oic.message import AuthorizationResponse
from oic.oic.message import EndSessionRequest
from oic.oic.message import IdToken
from oic.oic.message import OpenIDSchema
from pas.plugins.oidc.utils import SINGLE_OPTIONAL_BOOLEAN_AS_STRING
from plone import api
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from zExceptions import Unauthorized
from pas.plugins.oidc.plugins import OAuth2ConnectionException
from pas.plugins.oidc import _
from pas.plugins.oidc.utils import add_url_params

import base64
import json
import logging

try:
    # Python 3
    from urllib.parse import quote
except ImportError:
    # Python 2
    from urllib import quote


logger = logging.getLogger(__name__)


class Session(object):
    session_cookie_name = "__ac_session"
    _session = {}

    def __init__(self, request, use_session_data_manager=False):
        self.request = request
        self.use_session_data_manager = use_session_data_manager
        if self.use_session_data_manager:
            sdm = api.portal.get_tool("session_data_manager")
            self._session = sdm.getSessionData(create=True)
        else:
            data = self.request.cookies.get(self.session_cookie_name) or {}
            if data:
                data = json.loads(base64.b64decode(data))
            self._session = data

    def set(self, name, value):
        if self.use_session_data_manager:
            self._session.set(name, value)
        else:
            if self.get(name) != value:
                self._session[name] = value
                self.request.response.setCookie(
                    self.session_cookie_name,
                    base64.b64encode(
                        json.dumps(self._session).encode("utf-8")
                    ),
                )

    def get(self, name):
        # if self.use_session_data_manager:
        return self._session.get(name)

    def __repr__(self):
        return repr(self._session)


class RequireLoginView(BrowserView):
    """Our version of the require-login view from Plone.

    Our challenge plugin redirects here.
    Note that the plugin has no way of knowing if you are authenticated:
    its code is called before this is known.
    I think.
    """

    def __call__(self):
        if api.user.is_anonymous():
            # context is our PAS plugin
            url = self.context.absolute_url() + "/login"
            came_from = self.request.get("came_from", None)
            if came_from:
                url += "?came_from={}".format(quote(came_from))
        else:
            url = api.portal.get().absolute_url()
            url += "/insufficient-privileges"

        self.request.response.redirect(url)


class LoginView(BrowserView):
    def __call__(self):
        session = Session(
            self.request,
            use_session_data_manager=self.context.getProperty(
                "use_session_data_manager"
            ),
        )
        # state is used to keep track of responses to outstanding requests (state).
        # nonce is a string value used to associate a Client session with an ID Token, and to mitigate replay attacks.
        session.set("state", rndstr())
        session.set("nonce", rndstr())
        came_from = self.request.get("came_from")
        if came_from:
            session.set("came_from", came_from)

        try:
            client = self.context.get_oauth2_client()
        except OAuth2ConnectionException:
            portal_url = api.portal.get_tool("portal_url")
            if came_from and portal_url.isURLInPortal(came_from):
                return self.request.response.redirect(came_from)
            else:
                return self.request.response.redirect(
                    api.portal.get().absolute_url()
                )

        # https://pyoidc.readthedocs.io/en/latest/examples/rp.html#authorization-code-flow
        args = {
            "client_id": self.context.getProperty("client_id"),
            "response_type": "code",
            "scope": self.context.get_scopes(),
            "state": session.get("state"),
            "nonce": session.get("nonce"),
            "redirect_uri": self.context.get_redirect_uris(),
        }

        if self.context.getProperty("use_pkce"):
            # Build a random string of 43 to 128 characters
            # and send it in the request as a base64-encoded urlsafe string of the sha256 hash of that string
            session.set("verifier", rndstr(128))
            args["code_challenge"] = self.get_code_challenge(
                session.get("verifier")
            )
            args["code_challenge_method"] = "S256"

        try:
            auth_req = client.construct_AuthorizationRequest(request_args=args)
            login_url = auth_req.request(client.authorization_endpoint)
        except Exception as e:
            logger.error(e)
            api.portal.show_message(
                _(
                    "There was an error during the login process. Please try"
                    " again."
                )
            )
            portal_url = api.portal.get_tool("portal_url")
            if came_from and portal_url.isURLInPortal(came_from):
                self.request.response.redirect(came_from)
            else:
                self.request.response.redirect(api.portal.get().absolute_url())

            return

        self.request.response.setHeader(
            "Cache-Control", "no-cache, must-revalidate"
        )
        self.request.response.redirect(login_url)
        return

    def get_code_challenge(self, value):
        """build a sha256 hash of the base64 encoded value of value
        be careful: this should be url-safe base64 and we should also remove the trailing '='
        See https://www.stefaanlippens.net/oauth-code-flow-pkce.html#PKCE-code-verifier-and-challenge
        """
        hash_code = sha256(value.encode("utf-8")).digest()
        return (
            base64.urlsafe_b64encode(hash_code)
            .decode("utf-8")
            .replace("=", "")
        )


class LogoutView(BrowserView):
    def __call__(self):
        try:
            client = self.context.get_oauth2_client()
        except OAuth2ConnectionException:
            return ""

        # session = Session(
        #   self.request,
        #   use_session_data_manager=self.context.getProperty("use_session_data_manager")
        # )
        # state is used to keep track of responses to outstanding requests (state).
        # https://github.com/keycloak/keycloak-documentation/blob/master/securing_apps/topics/oidc/java/logout.adoc
        # session.set('end_session_state', rndstr())

        redirect_uri = api.portal.get().absolute_url()

        # Volto frontend mapping exception
        if redirect_uri.endswith("/api"):
            redirect_uri = redirect_uri[:-4]

        if self.context.getProperty("use_deprecated_redirect_uri_for_logout"):
            args = {
                "redirect_uri": redirect_uri,
            }
        else:
            args = {
                "post_logout_redirect_uri": redirect_uri,
                "client_id": self.context.getProperty("client_id"),
            }

        pas = getToolByName(self.context, "acl_users")
        auth_cookie_name = pas.credentials_cookie_auth.cookie_name

        # end_req = client.construct_EndSessionRequest(request_args=args)
        end_req = EndSessionRequest(**args)
        logout_url = end_req.request(client.end_session_endpoint)
        self.request.response.setHeader(
            "Cache-Control", "no-cache, must-revalidate"
        )
        # TODO: change path with portal_path
        self.request.response.expireCookie(auth_cookie_name, path="/")
        self.request.response.expireCookie("auth_token", path="/")
        self.request.response.redirect(logout_url)
        return


class CallbackView(BrowserView):
    def __call__(self):
        response = self.request.environ["QUERY_STRING"]
        session = Session(
            self.request,
            use_session_data_manager=self.context.getProperty(
                "use_session_data_manager"
            ),
        )
        client = self.context.get_oauth2_client()
        aresp = client.parse_response(
            AuthorizationResponse, info=response, sformat="urlencoded"
        )
        if aresp["state"] != session.get("state"):
            logger.error(
                "invalid OAuth2 state response:%s != session:%s",
                aresp.get("state"),
                session.get("state"),
            )
            # TODO: need to double check before removing the comment below
            # raise ValueError("invalid OAuth2 state")

        args = {
            "code": aresp["code"],
            "redirect_uri": self.context.get_redirect_uris(),
        }

        if self.context.getProperty("use_pkce"):
            args["code_verifier"] = session.get("verifier")

        if self.context.getProperty("use_modified_openid_schema"):
            IdToken.c_param.update(
                {
                    "email_verified": SINGLE_OPTIONAL_BOOLEAN_AS_STRING,
                    "phone_number_verified": SINGLE_OPTIONAL_BOOLEAN_AS_STRING,
                }
            )

        # Keep OIDC client usage for protocol/session handling, but verify
        # ID tokens through cryptojwt to support EU Login secp256k1.
        userinfo = None
        fallback_to_oic = False

        client_id = self.context.getProperty("client_id")
        client_secret = self.context.getProperty("client_secret")
        code_verifier = (
            session.get("verifier")
            if self.context.getProperty("use_pkce")
            else None
        )
        nonce = session.get("nonce")

        provider_info = getattr(client, "provider_info", {}) or {}
        jwks_uri = provider_info.get("jwks_uri")
        issuer = provider_info.get("issuer")
        supported_algs = provider_info.get(
            "id_token_signing_alg_values_supported"
        ) or ["ES256K"]
        if isinstance(supported_algs, str):
            supported_algs = [supported_algs]

        try:
            from pas.plugins.oidc.jwt_verification import (
                CompatibilityVerificationError,
                TokenValidationError,
                do_token_exchange,
                verify_id_token,
                verify_id_token_pyjwkest,
            )
        except Exception as exc:
            logger.warning(
                "JWT helper import failed, falling back to oic flow: %s", exc
            )
            fallback_to_oic = True

        if not fallback_to_oic:
            # Step 1: exchange authorization code for raw tokens.
            resp_dict = {}
            try:
                resp_dict = do_token_exchange(
                    client.token_endpoint,
                    aresp["code"],
                    self.context.get_redirect_uris(),
                    client_id,
                    client_secret,
                    code_verifier=code_verifier,
                )
            except Exception as exc:
                logger.warning(
                    "Token exchange failed in custom flow: %s", exc
                )
                fallback_to_oic = True

            # Step 2: verify ID token with cryptojwt.
            id_token_jwt = (resp_dict or {}).get("id_token")
            if not fallback_to_oic and not id_token_jwt:
                logger.warning(
                    "No id_token in token response, falling back to oic flow"
                )
                fallback_to_oic = True

            if not fallback_to_oic and not jwks_uri:
                logger.error("Missing jwks_uri in provider metadata")
                raise Unauthorized()

            if not fallback_to_oic:
                try:
                    userinfo = verify_id_token(
                        id_token_jwt,
                        jwks_uri,
                        issuer=issuer,
                        client_id=client_id,
                        nonce=nonce,
                        allowed_algs=supported_algs,
                    )
                    logger.info("cryptojwt verification succeeded")
                except CompatibilityVerificationError as exc:
                    logger.warning(
                        "cryptojwt compatibility issue: %s", exc
                    )
                    try:
                        userinfo = verify_id_token_pyjwkest(
                            id_token_jwt,
                            jwks_uri,
                            issuer=issuer,
                            client_id=client_id,
                            nonce=nonce,
                            allowed_algs=supported_algs,
                        )
                        logger.info("pyjwkest fallback succeeded")
                    except TokenValidationError as invalid_exc:
                        logger.warning(
                            "pyjwkest fallback rejected token: %s",
                            invalid_exc,
                        )
                        raise Unauthorized()
                    except Exception as fallback_exc:
                        logger.warning(
                            "pyjwkest fallback failed: %s", fallback_exc
                        )
                        raise Unauthorized()
                except TokenValidationError as exc:
                    # Security failure: do not fallback to weaker paths.
                    logger.warning("cryptojwt rejected token: %s", exc)
                    raise Unauthorized()
                except Exception as exc:
                    logger.warning(
                        "Unexpected cryptojwt verification failure: %s", exc
                    )
                    raise Unauthorized()

        # Step 3: operational fallback to the legacy oic path when the custom
        # token exchange flow is unavailable.
        if fallback_to_oic:
            logger.info("Falling back to oic do_access_token_request")
            resp = client.do_access_token_request(
                state=aresp["state"],
                request_args=args,
                authn_method="client_secret_basic",
            )

            if isinstance(resp, AccessTokenResponse):
                if client.userinfo_endpoint:
                    userinfo = client.do_user_info_request(
                        state=aresp["state"]
                    )
                else:
                    userinfo = resp.to_dict().get("id_token", {})
            else:
                logger.error("authentication failed %s", resp)
                raise Unauthorized()

        if userinfo is None:
            logger.error("authentication failed: missing userinfo")
            raise Unauthorized()

        # Handle the verified userinfo
        if userinfo and isinstance(userinfo, (OpenIDSchema, dict)):
            token = self.context.rememberIdentity(userinfo)
            self.request.response.setHeader(
                "Cache-Control", "no-cache, must-revalidate"
            )
            self.request.response.redirect(
                self.return_url(
                    session=session, userinfo=userinfo, token=token
                )
            )
            return
        else:
            logger.error(
                "authentication failed invalid response %s", userinfo
            )
            raise Unauthorized()

    def return_url(self, session=None, userinfo={}, token=None):
        came_from = self.request.get("came_from")
        if not came_from and session:
            came_from = session.get("came_from")

        portal_url = api.portal.get_tool("portal_url")
        if not (came_from and portal_url.isURLInPortal(came_from)):
            came_from = api.portal.get().absolute_url()

        # Volto frontend mapping exception
        if came_from.endswith("/api"):
            came_from = came_from[:-4]

        new_came_from = add_url_params(came_from, {"access_token": token})

        return new_came_from
