# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import INonInstallable
from zope.interface import implementer

import logging


logger = logging.getLogger(__name__)


@implementer(INonInstallable)
class HiddenProfiles(object):

    def getNonInstallableProfiles(self):
        """Hide uninstall profile from site-creation and quickinstaller."""
        return [
            'pas.plugins.oidc:uninstall',
        ]


def post_install(context):
    """Post install script"""
    # Setup our request oidc plugin.
    pas = getToolByName(context, 'acl_users')

    # Create plugin if it does not exist.
    from pas.plugins.oidc.plugins import OIDCPlugin
    from pas.plugins.oidc.utils import PLUGIN_ID
    if PLUGIN_ID not in pas.objectIds():
        plugin = OIDCPlugin(
            title='OpenID Connect',
        )
        plugin.id = PLUGIN_ID
        pas._setObject(PLUGIN_ID, plugin)
        logger.info('Created %s in acl_users.', PLUGIN_ID)
    plugin = getattr(pas, PLUGIN_ID)
    if not isinstance(plugin, OIDCPlugin):
        raise ValueError(
            'Existing PAS plugin {0} is not a OIDCPlugin.'.format(PLUGIN_ID))

    # # Activate all supported interfaces for this plugin.
    # activate = []
    # plugins = pas.plugins
    # for info in plugins.listPluginTypeInfo():
    #     interface = info['interface']
    #     interface_name = info['id']
    #     if plugin.testImplements(interface):
    #         activate.append(interface_name)
    #         logger.info(
    #             'Activating interface %s for plugin %s',
    #             interface_name, info['title'])

    # plugin.manage_activateInterfaces(activate)
    # logger.info('Plugins activated.')

    # Order some plugins to make sure our plugin is at the top.
    # This is not needed for all plugin interfaces.
    # for info in plugins.listPluginTypeInfo():
    #     interface_name = info['id']
    #     if interface_name in ['IChallengePlugin', 'IPropertiesPlugin']:
    #         iface = plugins._getInterfaceFromName(interface_name)
    #         for obj in plugins.listPlugins(iface):
    #             plugins.movePluginsUp(iface, [PLUGIN_ID])
    #         logger.info('Moved %s to top of %s.', PLUGIN_ID, interface_name)


def uninstall(context):
    """Uninstall script"""
    from pas.plugins.oidc.utils import PLUGIN_ID
    pas = getToolByName(context, 'acl_users')

    # Remove plugin if it exists.
    if PLUGIN_ID not in pas.objectIds():
        return
    from pas.plugins.oidc.plugins import OIDCPlugin
    plugin = getattr(pas, PLUGIN_ID)
    if not isinstance(plugin, OIDCPlugin):
        logger.warning(
            'PAS plugin %s not removed: it is not a OIDCPlugin.', PLUGIN_ID)
        return
    pas._delObject(PLUGIN_ID)
    logger.info('Removed OIDCPlugin %s from acl_users.', PLUGIN_ID)