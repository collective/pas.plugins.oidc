from pas.plugins.oidc import _
from pas.plugins.oidc import PLUGIN_ID
from pas.plugins.oidc.interfaces import IOIDCSettings
from plone import api
from plone.app.registry.browser import controlpanel
from plone.base.interfaces import IPloneSiteRoot
from zope.component import adapter
from zope.interface import implementer
from z3c.form.interfaces import DISPLAY_MODE


@adapter(IPloneSiteRoot)
@implementer(IOIDCSettings)
class OIDCControlPanelAdapter:
    propertymap = None

    def __init__(self, context):
        self.context = context
        self.portal = api.portal.get()
        self.encoding = "utf-8"
        self.settings = self.portal.acl_users[PLUGIN_ID]
        self.propertymap = {prop["id"]: prop for prop in self.settings.propertyMap()}

    def __getattr__(self, name):
        if self.propertymap and name in self.propertymap:
            return self.settings.getProperty(name)
        else:
            raise AttributeError(f"{name} not in oidcsettings")

    def __setattr__(self, name, value):
        if self.propertymap and name in self.propertymap:
            if "w" in self.propertymap[name].get("mode", ""):
                return setattr(self.settings, name, value)
            else:
                raise TypeError(f"{name} readonly in oidcsettings")
        else:
            super().__setattr__(name, value)


class OIDCSettingsForm(controlpanel.RegistryEditForm):
    schema = IOIDCSettings
    schema_prefix = "oidc_admin"
    label = _("OIDC Plugin Settings")
    description = ""

    def getContent(self):
        portal = api.portal.get()
        return OIDCControlPanelAdapter(portal)

    def updateWidgets(self):
        super().updateWidgets()
        pmap = self.getContent().settings.propertymap
        for name, widget in self.widgets.items():
            if name in pmap and "w" not in pmap[id].get("mode", ""):
                widget.mode = DISPLAY_MODE

    def applyChanges(self, data):
        """See interfaces.IEditForm"""
        content = self.getContent()
        changes = {}
        for name in data:
            current = getattr(content, name)
            value = data[name]
            if current != value:
                setattr(content, name, value)
                changes.setdefault(IOIDCSettings, []).append(name)
        return changes


class OIDCSettingsControlPanel(controlpanel.ControlPanelFormWrapper):
    form = OIDCSettingsForm
