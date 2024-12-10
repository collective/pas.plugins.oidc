from pas.plugins.oidc import _
from pas.plugins.oidc import PLUGIN_ID
from pas.plugins.oidc.interfaces import IOIDCSettings
from plone import api
from plone.app.registry.browser import controlpanel
from plone.base.interfaces import IPloneSiteRoot
from zope.component import adapter
from zope.interface import implementer


@adapter(IPloneSiteRoot)
@implementer(IOIDCSettings)
class OIDCControlPanelAdapter:

    def __init__(self, context):
        self.context = context
        self.portal = api.portal.get()
        self.encoding = "utf-8"
        self.settings = self.portal.acl_users[PLUGIN_ID]

    @property
    def issuer(self):
        return self.settings.issuer

    @issuer.setter
    def issuer(self, value):
        self.settings.issuer = value

    @property
    def client_id(self):
        return self.settings.client_id

    @client_id.setter
    def client_id(self, value):
        self.settings.client_id = value

    @property
    def client_secret(self):
        return self.settings.client_secret

    @client_secret.setter
    def client_secret(self, value):
        self.settings.client_secret = value

    @property
    def redirect_uris(self):
        return self.settings.redirect_uris

    @redirect_uris.setter
    def redirect_uris(self, value):
        self.settings.redirect_uris = value

    @property
    def use_session_data_manager(self):
        return self.settings.use_session_data_manager

    @use_session_data_manager.setter
    def use_session_data_manager(self, value):
        self.settings.use_session_data_manager = value

    @property
    def create_user(self):
        return self.settings.create_user

    @create_user.setter
    def create_user(self, value):
        self.settings.create_user = value

    @property
    def create_groups(self):
        return self.settings.create_groups

    @create_groups.setter
    def create_groups(self, value):
        self.settings.create_groups = value

    @property
    def user_property_as_groupid(self):
        return self.settings.user_property_as_groupid

    @user_property_as_groupid.setter
    def user_property_as_groupid(self, value):
        self.settings.user_property_as_groupid = value

    @property
    def create_ticket(self):
        return self.settings.create_ticket

    @create_ticket.setter
    def create_ticket(self, value):
        self.settings.create_ticket = value

    @property
    def create_restapi_ticket(self):
        return self.settings.create_restapi_ticket

    @create_restapi_ticket.setter
    def create_restapi_ticket(self, value):
        self.settings.create_restapi_ticket = value

    @property
    def scope(self):
        return self.settings.scope

    @scope.setter
    def scope(self, value):
        self.settings.scope = value

    @property
    def use_pkce(self):
        return self.settings.use_pkce

    @use_pkce.setter
    def use_pkce(self, value):
        self.settings.use_pkce = value

    @property
    def use_deprecated_redirect_uri_for_logout(self):
        return self.settings.use_deprecated_redirect_uri_for_logout

    @use_deprecated_redirect_uri_for_logout.setter
    def use_deprecated_redirect_uri_for_logout(self, value):
        self.settings.use_deprecated_redirect_uri_for_logout = value

    @property
    def use_modified_openid_schema(self):
        return self.settings.use_modified_openid_schema

    @use_modified_openid_schema.setter
    def use_modified_openid_schema(self, value):
        self.settings.use_modified_openid_schema = value

    @property
    def user_property_as_userid(self):
        return self.settings.user_property_as_userid

    @user_property_as_userid.setter
    def user_property_as_userid(self, value):
        self.settings.user_property_as_userid = value


class OIDCSettingsForm(controlpanel.RegistryEditForm):
    schema = IOIDCSettings
    schema_prefix = "oidc_admin"
    label = _("OIDC Plugin Settings")
    description = ""

    def getContent(self):
        portal = api.portal.get()
        return OIDCControlPanelAdapter(portal)

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
