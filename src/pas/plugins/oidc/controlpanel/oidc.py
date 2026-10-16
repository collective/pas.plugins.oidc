from pas.plugins.oidc import _
from pas.plugins.oidc.interfaces import IPasPluginsOidcLayer
from pas.plugins.oidc.interfaces import IOIDCControlpanel
from pas.plugins.oidc.interfaces import IOIDCSettings
from plone.restapi.controlpanels import RegistryConfigletPanel
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@adapter(Interface, IPasPluginsOidcLayer)
@implementer(IOIDCControlpanel)
class OIDCSettingsConfigletPanel(RegistryConfigletPanel):
    """Control Panel endpoint"""

    schema = IOIDCSettings
    configlet_id = "oidc_admin"
    configlet_category_id = "plone-users"
    title = _("OIDC settings")
    group = ""
