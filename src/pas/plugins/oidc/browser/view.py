from oic.oic.message import EndSessionRequest
from oic.oic.message import IdToken
from pas.plugins.oidc import _
from pas.plugins.oidc import logger
from pas.plugins.oidc import utils
from pas.plugins.oidc.plugins import OAuth2ConnectionException
from pas.plugins.oidc.session import Session
from plone import api
from Products.Five.browser import BrowserView
from urllib.parse import quote
from zExceptions import Unauthorized


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
            base_url = self.context.absolute_url()
            url = f"{base_url}/login"
            came_from = self.request.get("came_from", None)
            if came_from:
                url = f"{url}?came_from={quote(came_from)}"
        else:
            url = api.portal.get().absolute_url()
            url = f"{url}/insufficient-privileges"

        self.request.response.redirect(url)


class LoginView(BrowserView):
    def _internal_redirect_location(self, session: Session) -> str:
        came_from = session.get("came_from")
        portal_url = api.portal.get_tool("portal_url")
        if not (came_from and portal_url.isURLInPortal(came_from)):
            came_from = api.portal.get().absolute_url()
        return came_from

    def __call__(self):
        session = utils.initialize_session(self.context, self.request)
        args = utils.authorization_flow_args(self.context, session)
        error_msg = ""
        try:
            client = self.context.get_oauth2_client()
        except OAuth2ConnectionException:
            client = None
            error_msg = _("There was an error getting the oauth2 client.")
        if client:
            try:
                auth_req = client.construct_AuthorizationRequest(request_args=args)
                login_url = auth_req.request(client.authorization_endpoint)
            except Exception as e:
                logger.error(e)
                error_msg = _(
                    "There was an error during the login process. Please try again."
                )
            else:
                self.request.response.setHeader(
                    "Cache-Control", "no-cache, must-revalidate"
                )
                self.request.response.redirect(login_url)

        if error_msg:
            api.portal.show_message(error_msg)
            redirect_location = self._internal_redirect_location(session)
            self.request.response.redirect(redirect_location)
        return


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

        redirect_uri = utils.url_cleanup(api.portal.get().absolute_url())

        if self.context.getProperty("use_deprecated_redirect_uri_for_logout"):
            args = {
                "redirect_uri": redirect_uri,
            }
        else:
            args = {
                "post_logout_redirect_uri": redirect_uri,
                "client_id": self.context.getProperty("client_id"),
            }

        pas = api.portal.get_tool("acl_users")
        auth_cookie_name = pas.credentials_cookie_auth.cookie_name

        # end_req = client.construct_EndSessionRequest(request_args=args)
        end_req = EndSessionRequest(**args)
        logout_url = end_req.request(client.end_session_endpoint)
        self.request.response.setHeader("Cache-Control", "no-cache, must-revalidate")
        # TODO: change path with portal_path
        self.request.response.expireCookie(auth_cookie_name, path="/")
        self.request.response.expireCookie("auth_token", path="/")
        self.request.response.redirect(logout_url)
        return


class CallbackView(BrowserView):
    def __call__(self):
        session = utils.load_existing_session(self.context, self.request)
        client = self.context.get_oauth2_client()
        qs = self.request.environ["QUERY_STRING"]
        args, state = utils.parse_authorization_response(
            self.context, qs, client, session
        )
        if self.context.getProperty("use_modified_openid_schema"):
            IdToken.c_param.update(
                {
                    "email_verified": utils.SINGLE_OPTIONAL_BOOLEAN_AS_STRING,
                    "phone_number_verified": utils.SINGLE_OPTIONAL_BOOLEAN_AS_STRING,
                }
            )

        # The response you get back is an instance of an AccessTokenResponse
        # or again possibly an ErrorResponse instance.
        user_info = utils.get_user_info(client, state, args)
        if user_info:
            self.context.rememberIdentity(user_info)
            self.request.response.setHeader(
                "Cache-Control", "no-cache, must-revalidate"
            )
            return_url = utils.process_came_from(session, self.request.get("came_from"))
            self.request.response.redirect(return_url)
        else:
            raise Unauthorized()
