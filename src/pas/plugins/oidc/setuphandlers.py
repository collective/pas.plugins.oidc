from pas.plugins.oidc import logger
from pas.plugins.oidc import PLUGIN_ID
from pas.plugins.oidc import utils
from pas.plugins.oidc.plugins import OIDCPlugin
from plone import api
from Products.CMFPlone.interfaces import INonInstallable
from zope.interface import implementer


@implementer(INonInstallable)
class HiddenProfiles:
    def getNonInstallableProfiles(self):
        """Hide uninstall profile from site-creation and quickinstaller."""
        return [
            "pas.plugins.oidc:uninstall",
        ]


def post_install(context):
    """Post install script"""
    # Setup our request oidc plugin.
    pas = api.portal.get_tool("acl_users")

    # Create plugin if it does not exist.
    if PLUGIN_ID not in pas.objectIds():
        plugin = OIDCPlugin(
            id=PLUGIN_ID,
            title="OpenID Connect",
        )
        plugin.id = PLUGIN_ID
        pas._setObject(PLUGIN_ID, plugin)
        logger.info("Created %s in acl_users.", PLUGIN_ID)
    plugin = getattr(pas, PLUGIN_ID)
    if not isinstance(plugin, OIDCPlugin):
        raise ValueError(f"Existing PAS plugin {PLUGIN_ID} is not a OIDCPlugin.")

    # Activate all supported interfaces for this plugin.
    activate = []
    plugins = pas.plugins
    for info in plugins.listPluginTypeInfo():
        interface = info["interface"]
        interface_name = info["id"]
        if plugin.testImplements(interface):
            activate.append(interface_name)
            logger.info(f"Activating interface {interface_name} for plugin {PLUGIN_ID}")

    plugin.manage_activateInterfaces(activate)
    logger.info("Plugins activated.")

    # Order some plugins to make sure our plugin is at the top.
    # This is not needed for all plugin interfaces.
    for info in plugins.listPluginTypeInfo():
        interface_name = info["id"]
        # If we support IPropertiesPlugin, it should be added here.
        if interface_name in ("IChallengePlugin",):
            iface = plugins._getInterfaceFromName(interface_name)
            plugins.movePluginsTop(iface, [PLUGIN_ID])
            logger.info(f"Moved {PLUGIN_ID} to top of {interface_name}.")

    return plugin


def activate_plugin(context, interface_name, move_to_top=False):
    pas = api.portal.get_tool("acl_users")
    if PLUGIN_ID not in pas.objectIds():
        raise ValueError(f"acl_users has no plugin {PLUGIN_ID}.")

    plugin = getattr(pas, PLUGIN_ID)
    if not isinstance(plugin, OIDCPlugin):
        raise ValueError(f"Existing PAS plugin {PLUGIN_ID} is not a OIDCPlugin.")

    # This would activate one interface and deactivate all others:
    # plugin.manage_activateInterfaces([interface_name])
    # So only take over the necessary code from manage_activateInterfaces.
    plugins = pas.plugins
    iface = plugins._getInterfaceFromName(interface_name)
    if PLUGIN_ID not in plugins.listPluginIds(iface):
        plugins.activatePlugin(iface, PLUGIN_ID)
        logger.info(f"Activated interface {interface_name} for plugin {PLUGIN_ID}")

    if move_to_top:
        # Order some plugins to make sure our plugin is at the top.
        # This is not needed for all plugin interfaces.
        plugins.movePluginsTop(iface, [PLUGIN_ID])
        logger.info(f"Moved {PLUGIN_ID} to top of {interface_name}.")


def activate_challenge_plugin(context):
    activate_plugin(context, "IChallengePlugin", move_to_top=True)


def uninstall(context):
    """Uninstall script"""
    pas = api.portal.get_tool("acl_users")

    for plugin in utils.get_plugins():
        pas._delObject(plugin.getId())
        logger.info(f"Removed OIDCPlugin {plugin.getId()} from acl_users.")
