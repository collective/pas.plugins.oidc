from oic.oic.message import EndSessionRequest
from oic.oic.message import IdToken
from pas.plugins.oidc import _
from pas.plugins.oidc import logger
from pas.plugins.oidc import utils
from pas.plugins.oidc.plugins import OAuth2ConnectionException
from pas.plugins.oidc.plugins import OIDCPlugin
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from plone.restapi.deserializer import json_body
from plone.restapi.services import Service
from Products.PlonePAS.tools.memberdata import MemberData
from transaction.interfaces import NoTransaction
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse

import transaction


@implementer(IPublishTraverse)
class LoginOIDC(Service):
    """Base class for OIDC login."""

    _plugin: OIDCPlugin = None
    _data: dict = None
    provider_id: str = "oidc"

    def publishTraverse(self, request, name: str):
        # Store the first path segment as the provider
        request["TraversalRequestNameStack"] = []
        self.provider_id = name
        return self

    @property
    def json_body(self) -> dict:
        if not self._data:
            self._data = json_body(self.request)
        return self._data

    @property
    def plugin(self) -> OIDCPlugin:
        if not self._plugin:
            try:
                for plugin in utils.get_plugins():
                    if plugin.getId() == self.provider_id:
                        self._plugin = plugin
            except AttributeError:
                # Plugin not installed yet
                self._plugin = None
        return self._plugin

    def _provider_not_found(self, provider: str) -> dict:
        """Return 404 status code for a provider not found."""
        self.request.response.setStatus(404)
        message = (
            f"Provider {provider} is not available."
            if provider
            else "Provider was not informed."
        )
        return {
            "error": {
                "type": "Provider not found",
                "message": message,
            }
        }


class Get(LoginOIDC):
    """Provide information to start the OIDC flow."""

    def check_permission(self) -> bool:
        return True

    def reply(self) -> dict:
        """Generate URL and session information to be used by the frontend.

        :returns: URL and session information.
        """
        provider = self.provider_id
        plugin = self.plugin

        if not plugin:
            return self._provider_not_found(provider)

        session = utils.initialize_session(plugin, self.request)
        args = utils.authorization_flow_args(plugin, session)
        try:
            client = plugin.get_oauth2_client()
        except OAuth2ConnectionException:
            self.request.response.setStatus(500)
            return {
                "error": {
                    "type": "Configuration error",
                    "message": _("Provider is not properly configured."),
                }
            }
        try:
            auth_req = client.construct_AuthorizationRequest(request_args=args)
            login_url = auth_req.request(client.authorization_endpoint)
        except Exception as e:
            logger.error(e)
            self.request.response.setStatus(500)
            return {
                "error": {
                    "type": "Runtime error",
                    "message": _(
                        "There was an error during the login process. Please try again."
                    ),
                }
            }
        else:
            return {
                "next_url": login_url,
                "came_from": session.get("came_from"),
            }


class LogoutGet(LoginOIDC):
    """Logout a user."""

    def reply(self) -> dict:
        """Generate URL and session information to be used by the frontend.

        :returns: URL and session information.
        """
        plugin = self.plugin
        if not plugin:
            return self._provider_not_found(self.provider_id)

        try:
            client = plugin.get_oauth2_client()
        except OAuth2ConnectionException:
            self.request.response.setStatus(500)
            return {
                "error": {
                    "type": "Configuration error",
                    "message": _("Provider is not properly configured."),
                }
            }
        redirect_uri = utils.url_cleanup(api.portal.get().absolute_url())

        if plugin.getProperty("use_deprecated_redirect_uri_for_logout"):
            args = {
                "redirect_uri": redirect_uri,
            }
        else:
            args = {
                "post_logout_redirect_uri": redirect_uri,
                "client_id": plugin.getProperty("client_id"),
            }

        pas = api.portal.get_tool("acl_users")
        auth_cookie_name = pas.credentials_cookie_auth.cookie_name

        # end_req = client.construct_EndSessionRequest(request_args=args)
        end_req = EndSessionRequest(**args)
        logout_url = end_req.request(client.end_session_endpoint)
        self.request.response.expireCookie(auth_cookie_name, path="/")
        self.request.response.expireCookie("auth_token", path="/")
        return {
            "next_url": logout_url,
            "came_from": redirect_uri,
        }


class Post(LoginOIDC):
    """Handles OIDC login and returns a JSON web token (JWT)."""

    def check_permission(self) -> bool:
        return True

    def _annotate_transaction(self, action: str, user: MemberData):
        """Add a note to the current transaction."""
        try:
            # Get the current transaction
            tx = transaction.get()
        except NoTransaction:
            return None
        # Set user on the transaction
        tx.setUser(user.getUser())
        user_info = user.getProperty("fullname") or user.getUserName()
        msg = ""
        if action == "login":
            msg = f"(Logged in {user_info})"
        elif action == "add_identity":
            msg = f"(Added new identity to user {user_info})"
        tx.note(msg)

    def reply(self) -> dict:
        """Process callback, authenticate the user and return a JWT Token.

        :returns: Token information.
        """
        provider = self.provider_id
        plugin = self.plugin
        if not plugin:
            return self._provider_not_found(provider)

        session = utils.load_existing_session(plugin, self.request)
        client = plugin.get_oauth2_client()
        data = self.json_body
        qs = data.get("qs", "")
        qs = qs[1:] if qs.startswith("?") else qs
        args, state = utils.parse_authorization_response(plugin, qs, client, session)
        if plugin.getProperty("use_modified_openid_schema"):
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
            alsoProvides(self.request, IDisableCSRFProtection)
            action = "login"
            plugin.rememberIdentity(user_info)
            user_id = user_info["sub"]
            user = api.user.get(userid=user_id)
            token = self.request.response.cookies.get("auth_token", {}).get("value")
            # Make sure we are not setting cookies here
            # as it will break the authentication mechanism with JWT tokens
            self.request.response.cookies = {}
            self._annotate_transaction(action, user=user)
            return_url = utils.process_came_from(session)
            return {"token": token, "next_url": return_url}
        else:
            self.request.response.setStatus(401)
            return {
                "error": {
                    "type": "Authentication Error",
                    "message": "There was an issue authenticating this user",
                }
            }
