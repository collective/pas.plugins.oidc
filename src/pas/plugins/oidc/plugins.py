from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from contextlib import contextmanager
from oic.oauth2.message import ASConfigurationResponse
from oic.oic import Client
from oic.oic.message import OpenIDSchema
from oic.oic.message import RegistrationResponse
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from pas.plugins.oidc import logger
from plone.base.utils import safe_text
from plone.protect.utils import safeWrite
from Products.CMFCore.utils import getToolByName
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PlonePAS.events import UserInitialLoginInEvent
from Products.PlonePAS.events import UserLoggedInEvent
from Products.PluggableAuthService.events import PrincipalCreated
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import IChallengePlugin
from Products.PluggableAuthService.interfaces.plugins import IUserAdderPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.PropertiedUser import PropertiedUser
from Products.PluggableAuthService.utils import classImplements
from secrets import choice
from ZODB.POSException import ConflictError
from zope.event import notify
from zope.interface import implementer
from zope.interface import Interface

import itertools
import plone.api as api
import requests
import string


manage_addOIDCPluginForm = PageTemplateFile(
    "www/oidcPluginForm", globals(), __name__="manage_addOIDCPluginForm"
)


def addOIDCPlugin(dispatcher, id, title=None, REQUEST=None) -> None:  # noQA: A002
    """Add a HTTP Basic Auth Helper to a Pluggable Auth Service."""
    plugin = OIDCPlugin(id, title)
    dispatcher._setObject(plugin.getId(), plugin)

    if REQUEST is not None:
        url = dispatcher.absolute_url()
        message = "OIDC+Plugin+added."
        REQUEST["RESPONSE"].redirect(
            f"{url}/manage_workspace?manage_tabs_message={message}"
        )


PWCHARS = string.ascii_letters + string.digits + string.punctuation


def format_redirect_uris(uris: list[str]) -> list[str]:
    response = []
    portal_url = api.portal.get().absolute_url()
    for uri in uris:
        if uri.startswith("/"):
            uri = f"{portal_url}{uri}"
        response.append(safe_text(uri))
    return response


class OAuth2ConnectionException(Exception):
    """Exception raised when there are OAuth2 Connection Exceptions"""


class IOIDCPlugin(Interface):
    """OIDCPlugin Interface."""


class OAMClient(Client):
    """Override so we can adjust the jwks_uri to add domain needed for OAM"""

    def __init__(self, *args, domain=None, **xargs):
        super().__init__(self, *args, **xargs)
        self.domain = domain
        if domain:
            session = requests.Session()
            session.headers.update({"x-oauth-identity-domain-name": domain})
            self.settings.requests_session = session

    def handle_provider_config(
        self,
        pcr: ASConfigurationResponse,
        issuer: str,
        keys: bool = True,
        endpoints: bool = True,
    ) -> None:
        domain = self.domain
        if domain:
            # we need to modify jwks_uri in the provider_info to add
            # the identityDomain for OAM
            # gets used in https://github.com/CZ-NIC/pyoidc/blob/0bd1eadcefc5ccb7ef6c69d9b631537a7d3cfe30/src/oic/oauth2/__init__.py#L1132
            url = pcr["jwks_uri"]
            req = requests.PreparedRequest()
            req.prepare_url(url, {"identityDomainName": domain})
            pcr["jwks_uri"] = req.url
        return super().handle_provider_config(pcr, issuer, keys, endpoints)


@implementer(IOIDCPlugin)
class OIDCPlugin(BasePlugin):
    """PAS Plugin OpenID Connect."""

    meta_type = "OIDC Plugin"
    security = ClassSecurityInfo()

    title: str = "OIDC Plugin"
    issuer: str = ""
    client_id: str = ""
    client_secret: str = ""  # nosec B105
    redirect_uris: tuple[str] = ()
    use_session_data_manager: bool = False
    create_ticket: bool = True
    create_restapi_ticket: bool = False
    create_user: bool = True
    create_groups: bool = False
    user_property_as_groupid: str = "groups"
    allowed_groups: tuple[str] = ()
    scope: tuple[str] = ("profile", "email", "phone")
    use_pkce: bool = False
    use_deprecated_redirect_uri_for_logout: bool = False
    use_modified_openid_schema: bool = False
    user_property_as_userid: str = "sub"
    identity_domain_name: str = ""

    _properties: tuple[dict] = (
        {"id": "title", "type": "string", "mode": "w", "label": "Title"},
        {"id": "issuer", "type": "string", "mode": "w", "label": "OIDC/Oauth2 Issuer"},
        {"id": "client_id", "type": "string", "mode": "w", "label": "Client ID"},
        {
            "id": "client_secret",
            "type": "string",
            "mode": "w",
            "label": "Client secret",
        },
        {"id": "redirect_uris", "type": "lines", "mode": "w", "label": "Redirect uris"},
        {
            "id": "use_session_data_manager",
            "type": "boolean",
            "mode": "w",
            "label": "Use Zope session data manager.",
        },
        {
            "id": "create_user",
            "type": "boolean",
            "mode": "w",
            "label": "Create user / update user properties",
        },
        {
            "id": "create_groups",
            "type": "boolean",
            "mode": "w",
            "label": "Create groups / update group memberships",
        },
        {
            "id": "user_property_as_groupid",
            "type": "string",
            "mode": "w",
            "label": "User info property used as groupid, default 'groups'",
        },
        {
            "id": "allowed_groups",
            "type": "lines",
            "mode": "w",
            "label": "Allowed Groups",
        },
        {
            "id": "create_ticket",
            "type": "boolean",
            "mode": "w",
            "label": "Create authentication __ac ticket.",
        },
        {
            "id": "create_restapi_ticket",
            "type": "boolean",
            "mode": "w",
            "label": "Create authentication auth_token (volto/restapi) ticket.",
        },
        {
            "id": "scope",
            "type": "lines",
            "mode": "w",
            "label": "Open ID scopes to request to the server",
        },
        {"id": "use_pkce", "type": "boolean", "mode": "w", "label": "Use PKCE. "},
        {
            "id": "use_deprecated_redirect_uri_for_logout",
            "type": "boolean",
            "mode": "w",
            "label": (
                "Use deprecated redirect_uri for logout url"
                "(/Plone/acl_users/oidc/logout)."
            ),
        },
        {
            "id": "use_modified_openid_schema",
            "type": "boolean",
            "mode": "w",
            "label": (
                "Use a modified OpenID Schema for email_verified and "
                "phone_number_verified boolean values coming as string."
            ),
        },
        {
            "id": "user_property_as_userid",
            "type": "string",
            "mode": "w",
            "label": "User info property used as userid, default 'sub'",
        },
        {
            "id": "identity_domain_name",
            "type": "string",
            "mode": "w",
            "label": (
                "Identity Domain Name "
                "(required for Oracle Authentication Manager) only."
            ),
        },
    )

    def __init__(self, id, title=None):  # noQA: A002
        self._setId(id)
        self.title = title

    def _create_user(self, user_id: str) -> PropertiedUser:
        with safe_write(self.REQUEST):
            userAdders = self.plugins.listPlugins(IUserAdderPlugin)
            if not userAdders:
                raise NotImplementedError(
                    "I wanted to make a new user, but"
                    " there are no PAS plugins active"
                    " that can make users."
                )

            # Add the user to the first IUserAdderPlugin that works:
            user = None
            for _, curAdder in userAdders:
                if curAdder.doAddUser(user_id, self._generate_password()):
                    # Assign a dummy password. It'll never be used;.
                    user = self._getPAS().getUser(user_id)
                    try:
                        membershipTool = getToolByName(self, "portal_membership")
                        if not membershipTool.getHomeFolder(user_id):
                            membershipTool.createMemberArea(user_id)
                    except (ConflictError, KeyboardInterrupt):
                        raise
                    except Exception as exc:  # nosec B110
                        # Silently ignored exception, but seems fine here.
                        # Logging would likely generate too much noise,
                        # depending on your setup.
                        # https://bandit.readthedocs.io/en/1.7.4/plugins/b110_try_except_pass.html
                        logger.debug("Ignoring exception", exc_info=exc)
                        pass
                    else:
                        break
        return user

    def _update_user(
        self, user: PropertiedUser, userinfo: dict, first_login: bool
    ) -> None:
        with safe_write(self.REQUEST):
            # Update properties
            self._update_user_properties(user, userinfo)
        if first_login:
            notify(PrincipalCreated(user))
            notify(UserInitialLoginInEvent(user))
        notify(UserLoggedInEvent(user))

    def _create_update_groups(self, user: PropertiedUser, user_id: str, userinfo: dict):
        groupid_property = self.getProperty("user_property_as_groupid")
        group_ids = userinfo.get(groupid_property)
        if isinstance(group_ids, str):
            group_ids = [group_ids]

        if isinstance(group_ids, list):
            with safe_write(self.REQUEST):
                oidc = self.getId()
                groups = user.getGroups()
                # Remove group memberships
                for gid in groups:
                    group = api.group.get(gid)
                    is_managed = group.getProperty("type") == oidc.upper()
                    if is_managed and gid not in group_ids:
                        api.group.remove_user(group=group, username=user_id)
                # Add group memberships
                for gid in group_ids:
                    if gid not in groups:
                        group = api.group.get(gid) or api.group.create(gid, title=gid)
                        # Tag managed groups with "type" of plugin id
                        if not group.getTool().hasProperty("type"):
                            group.getTool()._setProperty("type", "", "string")
                        group.setGroupProperties({"type": oidc.upper()})
                        api.group.add_user(group=group, username=user_id)
        return user.getGroups()

    def _update_user_properties(self, user: PropertiedUser, userinfo: dict):
        """Update the given user properties from the set of credentials.
        This is utilised when first creating a user, and to update
        their information when logging in again later.
        """
        # TODO: Update it only if we change their data?
        # TODO: Add to config the mapping of OIDC metadata to Plone properties
        # TODO: Warning in case no user data is returned.
        user_props = {}
        email = userinfo.get("email", "")
        name = userinfo.get("name", "")
        given_name = userinfo.get("given_name", "")
        family_name = userinfo.get("family_name", "")
        if email:
            user_props["email"] = email
        if given_name and family_name:
            user_props["fullname"] = f"{given_name} {family_name}"
        elif name and family_name:
            user_props["fullname"] = f"{name} {family_name}"
        # user_props[LAST_UPDATE_USER_PROPERTY_KEY] = time.time()
        if user_props:
            user.setProperties(**user_props)

    def _generate_password(self):
        """Return a obfuscated password never used for login"""
        return "".join([choice(PWCHARS) for _ in range(40)])  # nosec B311

    def _setup_ticket(self, user_id: str):
        """Set up authentication ticket (__ac cookie) with plone.session.

        Only call this when self.create_ticket is True.
        """
        if not (pas := self._getPAS()) or ("session" not in pas):
            return
        info = pas._verifyUser(pas.plugins, user_id=user_id)
        if info is None:
            logger.debug("No user found matching header. Will not set up session.")
            return
        request = self.REQUEST
        response = request["RESPONSE"]
        pas.session._setupSession(user_id, response)
        logger.debug(f"Done setting up session/ticket for {user_id}")

    def _setup_jwt_ticket(self, user: PropertiedUser):
        """Set up JWT authentication ticket (auth_token cookie).

        Only call this when self.create_restapi_ticket is True.
        """
        authenticators = self.plugins.listPlugins(IAuthenticationPlugin)
        plugin = None
        for _, authenticator in authenticators:
            if authenticator.meta_type == "JWT Authentication Plugin":
                plugin = authenticator
                break
        if plugin:
            payload = {}
            payload["fullname"] = user.getProperty("fullname")
            token = plugin.create_token(user.getId(), data=payload)
            request = self.REQUEST
            response = request["RESPONSE"]
            # TODO: take care of path, cookiename and domain options ?
            response.setCookie("auth_token", token, path="/")

    # TODO: memoize (?)
    def get_oauth2_client(self):
        domain = self.getProperty("identity_domain_name")
        try:
            if domain:
                client = OAMClient(
                    client_authn_method=CLIENT_AUTHN_METHOD,
                    domain=domain,
                )
            else:
                client = Client(client_authn_method=CLIENT_AUTHN_METHOD)
            # Some providers aren't configured with configured and issuer urls the same
            # even though they should.
            client.allow["issuer_mismatch"] = True

            # use WebFinger
            info_ = client.provider_config(self.getProperty("issuer"))  # noqa: F841
            info = {
                "client_id": self.getProperty("client_id"),
                "client_secret": self.getProperty("client_secret"),
            }
            client_reg = RegistrationResponse(**info)
            client.store_registration_info(client_reg)
            return client
        except Exception as exc:
            # There may happen several connection errors in this process
            # we catch them here and raise a generic own exception to be able
            # to catch it wherever it happens without knowing the internals
            # of the OAuth2 process
            logger.exception("Error getting OAuth2 client", exc_info=exc)
            raise OAuth2ConnectionException from exc

    def rememberIdentity(self, userinfo):
        if not isinstance(userinfo, OpenIDSchema | dict):
            raise AssertionError(
                f"userinfo should be an OpenIDSchema but is {type(userinfo)}"
            )
        # sub: machine-readable identifier of the user at this server;
        #      this value is guaranteed to be unique per user, stable over time,
        #      and never re-used
        user_id = userinfo[self.getProperty("user_property_as_userid") or "sub"]

        # TODO: Configure userinfo/plone mapping
        if not (pas := self._getPAS()):
            return
        user = pas.getUserById(user_id)

        if not self.user_can_login(userinfo):
            message = "You are not allowed to log in due to group restrictions."
            api.portal.show_message(message=message, request=self.REQUEST, type="error")
            if user:
                raise AssertionError(
                    f"User {user_id} is not allowed to log in "
                    "due to group restrictions."
                )
            else:
                raise AssertionError(
                    "User is not allowed to log in due to group restrictions and will "
                    "not be created."
                )

        first_login = False
        if not user and self.getProperty("create_user"):
            user = self._create_user(user_id)
            first_login = bool(user)

        if user:
            # Update user
            self._update_user(user, userinfo=userinfo, first_login=first_login)

            if self.getProperty("create_groups"):
                self._create_update_groups(user, user_id, userinfo)

            if self.getProperty("create_ticket"):
                self._setup_ticket(user_id)

            if self.getProperty("create_restapi_ticket"):
                self._setup_jwt_ticket(user)

    def get_redirect_uris(self):
        redirect_uris = self.getProperty("redirect_uris")
        if redirect_uris:
            return format_redirect_uris(redirect_uris)
        return [
            f"{self.absolute_url()}/callback",
        ]

    def get_scopes(self) -> list[str]:
        if scopes := self.getProperty("scope"):
            return [safe_text(scope) for scope in scopes if scope]
        return []

    def challenge(self, request, response) -> bool:
        """Assert via the response that credentials will be gathered.

        For IChallengePlugin.

        Takes a REQUEST object and a RESPONSE object.

        Must return True if it fired, False/None otherwise.

        Note: if you are not logged in, and go to the login form,
        everything will still work, and you will not be challenged.
        A challenge is only tried when you are unauthorized.
        """
        # Go to the login view of the PAS plugin.
        logger.info("Challenge. Came from %s", request.URL)
        url = f"{self.absolute_url()}/require_login?came_from={request.URL}"
        response.redirect(url, lock=1)
        return True

    def user_can_login(self, userinfo: dict) -> bool:
        """Check if the user can login based on the allowed groups configuration

        Only call this when self.allowed_groups is not empty.
        """

        allowed_groups = self.getProperty("allowed_groups")
        if not allowed_groups:
            return True

        groupid_property = self.getProperty("user_property_as_groupid")

        groups = userinfo.get(groupid_property, [])
        if isinstance(groups, str):
            groups = [groups]

        for group in allowed_groups:
            if group in groups:
                return True

        logger.info(
            f"User is in groups: {groups} but allowed groups are: {allowed_groups}"
        )

        return False


InitializeClass(OIDCPlugin)

classImplements(
    OIDCPlugin,
    IOIDCPlugin,
    # IExtractionPlugin,
    # IAuthenticationPlugin,
    IChallengePlugin,
    # IPropertiesPlugin,
    # IRolesPlugin,
)


# https://github.com/collective/Products.AutoUserMakerPASPlugin/blob/master/Products/AutoUserMakerPASPlugin/auth.py
@contextmanager
def safe_write(request):
    """Disable CSRF protection of plone.protect for a block of code.
    Inside the context manager objects can be written to without any
    restriction. The context manager collects all touched objects
    and marks them as safe write."""
    # We used 'set' here before, but that could lead to:
    # TypeError: unhashable type: 'PersistentMapping'
    objects_before = _registered_objects(request)
    yield
    objects_after = _registered_objects(request)
    for obj in objects_after:
        if obj not in objects_before:
            safeWrite(obj, request)


def _registered_objects(request):
    """Collect all objects part of a pending write transaction."""
    app = request.PARENTS[-1]
    registered_objects = [
        conn._registered_objects
        # skip the 'temporary' connection since it stores session objects
        # which get written all the time
        for name, conn in app._p_jar.connections.items()
        if name != "temporary"
    ]
    return list(itertools.chain.from_iterable(registered_objects))
