"""Init and utils."""

from AccessControl.Permissions import manage_users as ManageUsers
from Products.PluggableAuthService import PluggableAuthService as PAS
from zope.i18nmessageid import MessageFactory

import logging


PACKAGE_NAME = "pas.plugins.oidc"
PLUGIN_ID = "oidc"

_ = MessageFactory(PACKAGE_NAME)

logger = logging.getLogger(PACKAGE_NAME)


def initialize(context):  # pragma: no cover
    """Initializer called when used as a Zope 2 product."""
    from pas.plugins.oidc import plugins

    PAS.registerMultiPlugin(plugins.OIDCPlugin.meta_type)

    context.registerClass(
        plugins.OIDCPlugin,
        permission=ManageUsers,
        constructors=(plugins.manage_addOIDCPluginForm, plugins.addOIDCPlugin),
        visibility=None,
    )
