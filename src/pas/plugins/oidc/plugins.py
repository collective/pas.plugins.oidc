# -*- coding: utf-8 -*-
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from contextlib import contextmanager
from oic.oic import Client
from oic.oic.message import OpenIDSchema
from oic.oic.message import RegistrationResponse
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from plone.protect.utils import safeWrite
from Products.CMFCore.utils import getToolByName

from Products.PluggableAuthService.interfaces.plugins import IChallengePlugin

# from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
# from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
# from Products.PluggableAuthService.interfaces.plugins import IRolesPlugin
from Products.PluggableAuthService.interfaces.plugins import (
    IAuthenticationPlugin,
)
from Products.PluggableAuthService.interfaces.plugins import IUserAdderPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from ZODB.POSException import ConflictError
from zope.component.hooks import getSite
from zope.interface import implementer
from zope.interface import Interface

import itertools
import logging
import os
import string

try:
    # Plone 6.0+
    from plone.base.utils import safe_text
except ImportError:
    # Plone 5.2
    from Products.CMFPlone.utils import safe_unicode as safe_text

try:
    # Python 3.6+
    from secrets import choice
except ImportError:
    # Less secure.
    # https://bandit.readthedocs.io/en/1.7.4/blacklists/blacklist_calls.html#b311-random
    from random import choice


logger = logging.getLogger(__name__)
# _MARKER = object()
PWCHARS = string.ascii_letters + string.digits + string.punctuation
# LAST_UPDATE_USER_PROPERTY_KEY = 'last_autousermaker_update'


def context_property(name, default=None):
    def getter(self, name=name, default=default):
        SITE_STRING = "_" + getSite().getId()
        # First of all try to get the value from
        # an environment variable that starts with
        # OIDC followed by property name and ends with Plone site id

        # This way we can handle several Plone sites in the same
        # zope instance and have different settings through environment
        # variables

        # i.e.: OIDC_USE_DATA_SESSION_MANAGER_Plone
        env_var = "OIDC" + name.upper() + SITE_STRING
        env_value = os.environ.get(env_var, default)

        if env_value == default:
            # Secondly, try to get the value from an environment
            # variable too, but this time without the Plone site id
            # i.e.: OIDC_USE_DATA_SESSION_MANAGER
            env_var = "OIDC" + name.upper() + SITE_STRING
            env_value = os.environ.get(env_var, default)

        if env_value == default:
            return env_value

        if isinstance(default, bool):
            if env_value.lower() == "true":
                return True

            if env_value.lower() == "false":
                return False

            return default

        if isinstance(default, tuple):
            if "," in env_value:
                env_value = tuple("".join(env_value.split()).split(","))
            else:
                if env_value == "":
                    return ()

                env_value = (env_value,)

        if env_value == "":
            return getattr(self, name)

        return env_value

    def setter(self, value, name=name):
        setattr(self, name, value)

    def deleter(self, name=name):
        delattr(self, name)

    return property(getter, setter, deleter)


class IOIDCPlugin(Interface):
    """ """


@implementer(IOIDCPlugin)
class OIDCPlugin(BasePlugin):
    """PAS Plugin OpenID Connect."""

    meta_type = "OIDC Plugin"
    security = ClassSecurityInfo()

    if os.environ.get("PAS_PLUGINS_OIDC_USE_ENVIRONMENT_VARS"):
        _issuer = ""
        _client_id = ""
        _client_secret = ""
        _redirect_uris = ()
        _use_session_data_manager = False
        _create_ticket = True
        _create_restapi_ticket = False
        _create_user = True
        _scope = ("profile", "email", "phone")
        _use_pkce = False
        _use_modified_openid_schema = False

        issuer = context_property("_issuer", "")
        client_id = context_property("_client_id", "")
        client_secret = context_property("_client_secret", "")
        redirect_uris = context_property("_redirect_uris", ())
        use_session_data_manager = context_property(
            "_use_session_data_manager", False
        )  # noqa
        create_ticket = context_property("_create_ticket", True)
        create_restapi_ticket = context_property(
            "_create_restapi_ticket", True
        )
        create_user = context_property("_create_user", True)
        scope = context_property("_scope", ("profile", "email", "phone"))
        use_pkce = context_property("_use_pkce", True)
        use_modified_openid_schema = context_property(
            "_use_modified_openid_schema", False
        )  # noqa

    else:
        issuer = ""
        client_id = ""
        client_secret = ""  # nosec B105
        redirect_uris = ()
        use_session_data_manager = False
        create_ticket = True
        create_restapi_ticket = False
        create_user = True
        scope = ("profile", "email", "phone")
        use_pkce = False
        use_modified_openid_schema = False

    _properties = (
        dict(id="issuer", type="string", mode="w", label="OIDC/Oauth2 Issuer"),
        dict(id="client_id", type="string", mode="w", label="Client ID"),
        dict(
            id="client_secret", type="string", mode="w", label="Client secret"
        ),
        dict(
            id="redirect_uris", type="lines", mode="w", label="Redirect uris"
        ),
        dict(
            id="use_session_data_manager",
            type="boolean",
            mode="w",
            label="Use Zope session data manager.",
        ),
        dict(
            id="create_user",
            type="boolean",
            mode="w",
            label="Create user / update user properties",
        ),
        dict(
            id="create_ticket",
            type="boolean",
            mode="w",
            label="Create authentication __ac ticket. ",
        ),
        dict(
            id="create_restapi_ticket",
            type="boolean",
            mode="w",
            label="Create authentication auth_token (volto/restapi) ticket.",
        ),
        dict(
            id="scope",
            type="lines",
            mode="w",
            label="Open ID scopes to request to the server",
        ),
        dict(id="use_pkce", type="boolean", mode="w", label="Use PKCE. "),
        dict(
            id="use_modified_openid_schema",
            type="boolean",
            mode="w",
            label=(
                "Use a modified OpenID Schema for email_verified and"
                " phone_number_verified boolean values coming as string. "
            ),
        ),
    )

    def rememberIdentity(self, userinfo):
        if not isinstance(userinfo, OpenIDSchema):
            raise AssertionError(
                "userinfo should be an OpenIDSchema but is {}".format(
                    type(userinfo)
                )
            )
        # sub: machine-readable identifier of the user at this server;
        #      this value is guaranteed to be unique per user, stable over time,
        #      and never re-used
        user_id = userinfo["sub"]
        # TODO: configurare userinfo/plone mapping
        pas = self._getPAS()
        if pas is None:
            return
        user = pas.getUserById(user_id)
        if self.getProperty("create_user"):
            # https://github.com/collective/Products.AutoUserMakerPASPlugin/blob/master/Products/AutoUserMakerPASPlugin/auth.py#L110
            if user is None:
                with safe_write(self.REQUEST):
                    userAdders = self.plugins.listPlugins(IUserAdderPlugin)
                    if not userAdders:
                        raise NotImplementedError(
                            "I wanted to make a new user, but"
                            " there are no PAS plugins active"
                            " that can make users."
                        )
                    # roleAssigners = self.plugins.listPlugins(IRoleAssignerPlugin)
                    # if not roleAssigners:
                    #     raise NotImplementedError("I wanted to make a new user and give"
                    #                             " him the Member role, but there are"
                    #                             " no PAS plugins active that assign"
                    #                             " roles to users.")

                    # Add the user to the first IUserAdderPlugin that works:
                    user = None
                    for _, curAdder in userAdders:
                        if curAdder.doAddUser(
                            user_id, self._generatePassword()
                        ):
                            # Assign a dummy password. It'll never be used;.
                            user = self._getPAS().getUser(user_id)
                            try:
                                membershipTool = getToolByName(
                                    self, "portal_membership"
                                )
                                if not membershipTool.getHomeFolder(user_id):
                                    membershipTool.createMemberArea(user_id)
                            except (ConflictError, KeyboardInterrupt):
                                raise
                            except Exception:  # nosec B110
                                # Silently ignored exception, but seems fine here.
                                # Logging would likely generate too much noise,
                                # depending on your setup.
                                # https://bandit.readthedocs.io/en/1.7.4/plugins/b110_try_except_pass.html
                                pass
                            self._updateUserProperties(user, userinfo)
                            break
            else:
                # if time.time() > user.getProperty(LAST_UPDATE_USER_PROPERTY_KEY) + config.get(autoUpdateUserPropertiesIntervalKey, 0):
                with safe_write(self.REQUEST):
                    self._updateUserProperties(user, userinfo)
        if user and self.getProperty("create_ticket"):
            self._setupTicket(user_id)
        if user and self.getProperty("create_restapi_ticket"):
            self._setupJWTTicket(user_id, user)

    def _updateUserProperties(self, user, userinfo):
        """Update the given user properties from the set of credentials.
        This is utilised when first creating a user, and to update
        their information when logging in again later.
        """
        # TODO: modificare solo se ci sono dei cambiamenti sui dati ?
        # TODO: mettere in config il mapping tra metadati che arrivano da oidc e properties su plone
        # TODO: warning nel caso non vengono tornati dati dell'utente
        userProps = {}
        if "email" in userinfo:
            userProps["email"] = userinfo["email"]
        if "given_name" in userinfo and "family_name" in userinfo:
            userProps["fullname"] = "{} {}".format(
                userinfo["given_name"], userinfo["family_name"]
            )
        elif "name" in userinfo and "family_name" in userinfo:
            userProps["fullname"] = "{} {}".format(
                userinfo["name"], userinfo["family_name"]
            )
        # userProps[LAST_UPDATE_USER_PROPERTY_KEY] = time.time()
        if userProps:
            user.setProperties(**userProps)

    def _generatePassword(self):
        """Return a obfuscated password never used for login"""
        return "".join([choice(PWCHARS) for ii in range(40)])  # nosec B311

    def _setupTicket(self, user_id):
        """Set up authentication ticket (__ac cookie) with plone.session.

        Only call this when self.create_ticket is True.
        """
        pas = self._getPAS()
        if pas is None:
            return
        if "session" not in pas:
            return
        info = pas._verifyUser(pas.plugins, user_id=user_id)
        if info is None:
            logger.debug(
                "No user found matching header. Will not set up session."
            )
            return
        request = self.REQUEST
        response = request["RESPONSE"]
        pas.session._setupSession(user_id, response)
        logger.debug("Done setting up session/ticket for %s" % user_id)

    def _setupJWTTicket(self, user_id, user):
        """Set up JWT authentication ticket (auth_token cookie).

        Only call this when self.create_restapi_ticket is True.
        """
        authenticators = self.plugins.listPlugins(IAuthenticationPlugin)
        plugin = None
        for id_, authenticator in authenticators:
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
        client = Client(client_authn_method=CLIENT_AUTHN_METHOD)
        # registration_response = client.register(provider_info["registration_endpoint"], redirect_uris=...)
        # ... oic.exception.RegistrationError: {'error': 'insufficient_scope',
        #     'error_description': "Policy 'Trusted Hosts' rejected request to client-registration service. Details: Host not trusted."}

        # use WebFinger
        provider_info = client.provider_config(
            self.getProperty("issuer")
        )  # noqa
        info = {
            "client_id": self.getProperty("client_id"),
            "client_secret": self.getProperty("client_secret"),
        }
        client_reg = RegistrationResponse(**info)
        client.store_registration_info(client_reg)
        return client

    def get_redirect_uris(self):
        redirect_uris = self.getProperty("redirect_uris")
        if redirect_uris:
            return [safe_text(uri) for uri in redirect_uris if uri]
        return [
            "{}/callback".format(self.absolute_url()),
        ]

    def get_scopes(self):
        scopes = self.getProperty("scope")
        if scopes:
            return [safe_text(scope) for scope in scopes if scope]
        return []

    def challenge(self, request, response):
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
        url = "{}/require_login?came_from={}".format(
            self.absolute_url(), request.URL
        )
        response.redirect(url, lock=1)
        return True


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


def add_oidc_plugin():
    # Form for manually adding our plugin.
    # But we do this in setuphandlers.py always.
    pass


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
    return list(
        itertools.chain.from_iterable(
            [
                conn._registered_objects
                # skip the 'temporary' connection since it stores session objects
                # which get written all the time
                for name, conn in app._p_jar.connections.items()
                if name != "temporary"
            ]
        )
    )
