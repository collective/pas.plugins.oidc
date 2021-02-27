import json
import base64
from Products.Five.browser import BrowserView
from oic.oic import Client
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from oic.oic.message import AuthorizationResponse
from oic import rndstr
from plone import api


# https://zope.readthedocs.io/en/latest/zopebook/Sessions.html#alternative-server-side-session-backends-for-zope-4
# in produzione usare: https://pypi.org/project/Products.mcdutils/
# XXX: attualmente implementata sessione su cookie
class Session(object):
    session_cookie_name = '__ac_session'
    _session = {}

    def __init__(self, request, use_session_data_manager=False):
        self.request = request
        self.use_session_data_manager = use_session_data_manager
        if self.use_session_data_manager:
            sdm = api.portal.get_tool('session_data_manager')
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
                    base64.b64encode(json.dumps(self._session).encode('utf-8'))
                )

    def get(self, name):
        # if self.use_session_data_manager:
        return self._session.get(name)

    def __repr__(self):
        return repr(self._session)


class LoginView(BrowserView):

    def __call__(self):
        session = Session(self.request, use_session_data_manager=self.context.use_session_data_manager)
        # state is used to keep track of responses to outstanding requests (state).
        # nonce is a string value used to associate a Client session with an ID Token, and to mitigate replay attacks.
        session.set('state', rndstr())
        session.set('nonce', rndstr())

        client = self.context.get_oauth2_client()

        # https://pyoidc.readthedocs.io/en/latest/examples/rp.html#authorization-code-flow
        args = {
            'client_id':'valbisenzio-staging-c1', 
            'response_type': 'code', 
            'scope': ['profile', 'email', 'phone'],
            'state': session.get('state'),
            'nonce': session.get('nonce'),
            "redirect_uri": self.context.get_redirect_uris(),
        }
        auth_req = client.construct_AuthorizationRequest(request_args=args)
        login_url = auth_req.request(client.authorization_endpoint)
        self.request.response.setHeader("Cache-Control", "no-cache, must-revalidate")
        self.request.response.redirect(login_url)
        return
        

# https://valbisenzio.agamar.redturtle.it/oidc/callback?....
class CallbackView(BrowserView):
    def __call__(self):
        response = self.request.environ["QUERY_STRING"]
        session = Session(self.request, use_session_data_manager=self.context.use_session_data_manager)
        client = self.context.get_oauth2_client()

        aresp = client.parse_response(
            AuthorizationResponse, info=response, sformat="urlencoded")
        assert aresp["state"] == session.get("state")
        args = {
            "code": aresp["code"],
            "redirect_uri": self.context.get_redirect_uris(),
        }
        resp = client.do_access_token_request(
            state=aresp["state"], 
            request_args=args, 
            authn_method="client_secret_basic"
        )

        userinfo = client.do_user_info_request(state=aresp["state"])

        self.context.rememberIdentity(userinfo)

        # TODO: manage next_url/came_from
        # self.request.response.redirect(api.portal.get().absolute_url())
        return userinfo.to_json()
