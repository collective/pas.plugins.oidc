# -*- coding: utf-8 -*-
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from contextlib import contextmanager
from oic.oic import Client
from oic.oic.message import RegistrationResponse
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from plone import api
from plone.protect.utils import safeWrite
from Products.CMFCore.utils import getToolByName
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin  # noqa
from Products.PluggableAuthService.interfaces.plugins import IChallengePlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
from Products.PluggableAuthService.interfaces.plugins import IRolesPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserAdderPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from random import choice
from ZODB.POSException import ConflictError
from zope.interface import Interface
from zope.interface import implementer

import itertools
import logging
import six
import string
import time


logger = logging.getLogger(__name__)
# _MARKER = object()
PWCHARS = string.ascii_letters + string.digits + string.punctuation
# LAST_UPDATE_USER_PROPERTY_KEY = 'last_autousermaker_update'


class IOIDCPlugin(Interface):
    """ """


@implementer(IOIDCPlugin)
class OIDCPlugin(BasePlugin):
    """PAS Plugin OpenID Connect.
    """

    meta_type = 'OIDC Plugin'
    security = ClassSecurityInfo()

    issuer = ''
    client_id = ''
    client_secret = ''
    redirect_uris = ()
    use_session_data_manager = False
    create_ticket = True
    create_restapi_ticket = False
    create_user = True
    scope = ('profile', 'email', 'phone')
    use_pkce = False

    _properties = (
        dict(id='issuer', type='string', mode='w',
             label='OIDC/Oauth2 Issuer'),
        dict(id='client_id', type='string', mode='w',
             label='Client ID'),
        dict(id='client_secret', type='string', mode='w',
             label='Client secret'),
        dict(id='redirect_uris', type='lines', mode='w',
             label='Redirect uris'),
        dict(id='use_session_data_manager', type='boolean', mode='w',
             label='Use Zope session data manager.'),
        dict(id='create_user', type='boolean', mode='w',
             label='Create user / update user properties'),
        dict(id='create_ticket', type='boolean', mode='w',
             label='Create authentication __ac ticket. '),
        dict(id='create_restapi_ticket', type='boolean', mode='w',
             label='Create authentication auth_token (volto/restapi) ticket.'),
        dict(id='scope', type='lines', mode='w',
             label='Open ID scopes to request to the server'),
        dict(id='use_pkce', type='boolean', mode='w',
             label='Use PKCE. '),

    )

    def rememberIdentity(self, userinfo):
        # TODO: configurare mapping
        user_id = userinfo['preferred_username']
        pas = self._getPAS()
        if pas is None:
            return
        user = pas.getUserById(user_id)
        if self.create_user:
            # https://github.com/collective/Products.AutoUserMakerPASPlugin/blob/master/Products/AutoUserMakerPASPlugin/auth.py#L110
            if user is None:
                with safe_write(self.REQUEST):
                    userAdders = self.plugins.listPlugins(IUserAdderPlugin)
                    if not userAdders:
                        raise NotImplementedError("I wanted to make a new user, but"
                                                " there are no PAS plugins active"
                                                " that can make users.")
                    # roleAssigners = self.plugins.listPlugins(IRoleAssignerPlugin)
                    # if not roleAssigners:
                    #     raise NotImplementedError("I wanted to make a new user and give"
                    #                             " him the Member role, but there are"
                    #                             " no PAS plugins active that assign"
                    #                             " roles to users.")

                    # Add the user to the first IUserAdderPlugin that works:
                    user = None
                    for _, curAdder in userAdders:
                        if curAdder.doAddUser(user_id, self._generatePassword()):
                            # Assign a dummy password. It'll never be used;.
                            user = self._getPAS().getUser(user_id)
                            try:
                                membershipTool = getToolByName(self, 'portal_membership')
                                if not membershipTool.getHomeFolder(user_id):
                                    membershipTool.createMemberArea(user_id)
                            except (ConflictError, KeyboardInterrupt):
                                raise
                            except Exception:
                                pass
                            self._updateUserProperties(user, userinfo)
                            break
            else:
                # if time.time() > user.getProperty(LAST_UPDATE_USER_PROPERTY_KEY) + config.get(autoUpdateUserPropertiesIntervalKey, 0):
                with safe_write(self.REQUEST):
                    self._updateUserProperties(user, userinfo)
        if user and self.create_ticket:
            self._setupTicket(user_id)
        if user and self.create_restapi_ticket:
            self._setupJWTTicket(user_id, user)

    def _updateUserProperties(self, user, userinfo):
        """ Update the given user properties from the set of credentials.
        This is utilised when first creating a user, and to update
        their information when logging in again later.
        """
        # TODO: modificare solo se ci sono dei cambiamenti sui dati ?
        # TODO: mettere in config il mapping tra metadati che arrivano da oidc e properties su plone
        # TODO: warning nel caso non vengono tornati dati dell'utente
        userProps = {}
        if 'email' in userinfo:
            userProps['email'] = userinfo['email']
        if 'name' in userinfo and 'family_name' in userinfo:
            userProps['fullname'] = '{} {}'.format(userinfo['name'], userinfo['family_name'])
        # userProps[LAST_UPDATE_USER_PROPERTY_KEY] = time.time()
        if userProps:
            user.setProperties(**userProps)

    def _generatePassword(self):
        """ Return a obfuscated password never used for login """
        return ''.join([choice(PWCHARS) for ii in range(40)])

    def _setupTicket(self, user_id):
        """Set up authentication ticket (__ac cookie) with plone.session.

        Only call this when self.create_ticket is True.
        """
        pas = self._getPAS()
        if pas is None:
            return
        if 'session' not in pas:
            return
        info = pas._verifyUser(pas.plugins, user_id=user_id)
        if info is None:
            logger.debug('No user found matching header. Will not set up session.')
            return
        request = self.REQUEST
        response = request['RESPONSE']
        pas.session._setupSession(user_id, response)
        logger.debug('Done setting up session/ticket for %s' % user_id)

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
            response = request['RESPONSE']
            # TODO: take care of path, cookiename and domain options ?
            response.setCookie('auth_token', token, path='/')

    # TODO: memoize (?)
    def get_oauth2_client(self):
        client = Client(client_authn_method=CLIENT_AUTHN_METHOD)
        # registration_response = client.register(provider_info["registration_endpoint"], redirect_uris=...)
        # ... oic.exception.RegistrationError: {'error': 'insufficient_scope',
        #     'error_description': "Policy 'Trusted Hosts' rejected request to client-registration service. Details: Host not trusted."}

        # use WebFinger
        provider_info = client.provider_config(self.issuer)
        info = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        client_reg = RegistrationResponse(**info)
        client.store_registration_info(client_reg)
        return client

    def get_redirect_uris(self):
        if self.redirect_uris:
            return [u.decode('utf-8') for u in self.redirect_uris]
        else:
            return [
                '{}/callback'.format(self.absolute_url()),
            ]

    def get_scopes(self):
        if self.scope:
            return [u.decode('utf-8') for u in self.scope]
        else:
            return []


InitializeClass(OIDCPlugin)

classImplements(
    OIDCPlugin,
    IOIDCPlugin,
    # IExtractionPlugin,
    # IAuthenticationPlugin,
    # IChallengePlugin,
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
    objects_before = set(_registered_objects(request))
    yield
    objects_after = set(_registered_objects(request))
    for obj in objects_after - objects_before:
        safeWrite(obj, request)


def _registered_objects(request):
    """Collect all objects part of a pending write transaction."""
    app = request.PARENTS[-1]
    return list(itertools.chain.from_iterable(
        [conn._registered_objects
         # skip the 'temporary' connection since it stores session objects
         # which get written all the time
         for name, conn in app._p_jar.connections.items() if name != 'temporary'
        ]
    ))
