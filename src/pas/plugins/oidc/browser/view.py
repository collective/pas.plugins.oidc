from hashlib import sha256
from oic import rndstr
from oic.oic import Client
from oic.oic.message import AuthorizationResponse
from oic.oic.message import EndSessionRequest
from oic.oic.message import IdToken
from pas.plugins.oidc.utils import CustomOpenIDNonBooleanSchema
from pas.plugins.oidc.utils import SINGLE_OPTIONAL_BOOLEAN_AS_STRING
from plone import api
from Products.Five.browser import BrowserView

import base64
import json
import logging


logger = logging.getLogger(__name__)


# https://zope.readthedocs.io/en/latest/zopebook/Sessions.html#alternative-server-side-session-backends-for-zope-4
# in produzione usare: https://pypi.org/project/Products.mcdutils/
# XXX: attualmente implementata sessione su cookie
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
                    base64.b64encode(json.dumps(self._session).encode("utf-8")),
                )

    def get(self, name):
        # if self.use_session_data_manager:
        return self._session.get(name)

    def __repr__(self):
        return repr(self._session)


class LoginView(BrowserView):
    def __call__(self):
        session = Session(
            self.request, use_session_data_manager=self.context.use_session_data_manager
        )
        # state is used to keep track of responses to outstanding requests (state).
        # nonce is a string value used to associate a Client session with an ID Token, and to mitigate replay attacks.
        session.set("state", rndstr())
        session.set("nonce", rndstr())
        came_from = self.request.get("came_from")
        if came_from:
            session.set("came_from", came_from)

        client = self.context.get_oauth2_client()

        # https://pyoidc.readthedocs.io/en/latest/examples/rp.html#authorization-code-flow
        args = {
            "client_id": self.context.client_id,
            "response_type": "code",
            "scope": self.context.get_scopes(),
            "state": session.get("state"),
            "nonce": session.get("nonce"),
            "redirect_uri": self.context.get_redirect_uris(),
        }

        if self.context.use_pkce:
            # Build a random string of 43 to 128 characters
            # and send it in the request as a base64-encoded urlsafe string of the sha256 hash of that string
            session.set("verifier", rndstr(128))
            args["code_challenge"] = self.get_code_challenge(session.get("verifier"))
            args["code_challenge_method"] = "S256"

        auth_req = client.construct_AuthorizationRequest(request_args=args)
        login_url = auth_req.request(client.authorization_endpoint)
        self.request.response.setHeader("Cache-Control", "no-cache, must-revalidate")
        self.request.response.redirect(login_url)
        return

    def get_code_challenge(self, value):
        """build a sha256 hash of the base64 encoded value of value
        be careful: this should be url-safe base64 and we should also remove the trailing '='
        See https://www.stefaanlippens.net/oauth-code-flow-pkce.html#PKCE-code-verifier-and-challenge
        """
        hash_code = sha256(value.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(hash_code).decode("utf-8").replace("=", "")


class LogoutView(BrowserView):
    def __call__(self):
        client = self.context.get_oauth2_client()
        # session = Session(self.request, use_session_data_manager=self.context.use_session_data_manager)
        # state is used to keep track of responses to outstanding requests (state).
        # https://github.com/keycloak/keycloak-documentation/blob/master/securing_apps/topics/oidc/java/logout.adoc
        # session.set('end_session_state', rndstr())
        args = {
            # 'state': session.get('end_session_state'),
            # TODO: ....
            # 'post_logout_redirect_uri': api.portal.get().absolute_url(),
            "redirect_uri": api.portal.get().absolute_url(),
        }
        # end_req = client.construct_EndSessionRequest(request_args=args)
        end_req = EndSessionRequest(**args)
        logout_url = end_req.request(client.end_session_endpoint)
        self.request.response.setHeader("Cache-Control", "no-cache, must-revalidate")
        # TODO: change path with portal_path
        self.request.response.expireCookie("__ac", path="/")
        self.request.response.expireCookie("auth_token", path="/")
        self.request.response.redirect(logout_url)
        return


class CallbackView(BrowserView):
    def __call__(self):
        response = self.request.environ["QUERY_STRING"]
        session = Session(
            self.request, use_session_data_manager=self.context.use_session_data_manager
        )
        client = self.context.get_oauth2_client()
        aresp = client.parse_response(
            AuthorizationResponse, info=response, sformat="urlencoded"
        )
        # XXX: togliere debug e reinserire assert dopo aver trovato eventuali
        # anomalie
        logger.info("DEBUG %s %s", aresp.get("state"), session.get("state"))
        # assert aresp["state"] == session.get("state")
        args = {
            "code": aresp["code"],
            "redirect_uri": self.context.get_redirect_uris(),
        }

        if self.context.use_pkce:
            args["code_verifier"] = session.get("verifier")

        if self.context.use_modified_openid_schema:
            IdToken.c_param.update(
                {
                    "email_verified": SINGLE_OPTIONAL_BOOLEAN_AS_STRING,
                    "phone_number_verified": SINGLE_OPTIONAL_BOOLEAN_AS_STRING,
                }
            )
        resp = client.do_access_token_request(
            state=aresp["state"],
            request_args=args,
            authn_method="client_secret_basic",
        )

        if client.userinfo_endpoint:
            # XXX: Not completely sure if this is even needed
            #      We do not have a OpenID connect provider with userinfo endpoint
            #      enabled and with the weird treatment of boolean values, so we cannot test this
            # if self.context.use_modified_openid_schema:
            #     userinfo = client.do_user_info_request(state=aresp["state"], user_info_schema=CustomOpenIDNonBooleanSchema)
            # else:
            #     userinfo = client.do_user_info_request(state=aresp["state"])
            userinfo = client.do_user_info_request(state=aresp["state"])
        else:
            userinfo = resp.to_dict().get("id_token", {})

        # session.set('id_token', )
        self.context.rememberIdentity(userinfo)
        self.request.response.setHeader("Cache-Control", "no-cache, must-revalidate")
        self.request.response.redirect(self.return_url(session=session))
        # return userinfo.to_json()
        return

    def return_url(self, session=None):
        came_from = self.request.get("came_from")
        if not came_from and session:
            came_from = session.get("came_from")
        if came_from:
            return came_from
        else:
            return api.portal.get().absolute_url()