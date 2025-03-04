from pas.plugins.oidc import PLUGIN_ID
from pas.plugins.oidc.interfaces import IOIDCControlpanel
from pas.plugins.oidc.plugins import OIDCPlugin
from plone import api
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.serializer.controlpanels import ControlpanelSerializeToJson
from plone.restapi.serializer.controlpanels import get_jsonschema_for_controlpanel
from plone.restapi.serializer.controlpanels import SERVICE_ID
from zope.component import adapter
from zope.interface import implementer


@implementer(ISerializeToJson)
@adapter(IOIDCControlpanel)
class OIDCControlpanelSerializeToJson(ControlpanelSerializeToJson):
    def config_data(self) -> dict:
        data = {}
        portal = api.portal.get()
        plugin = portal.acl_users[PLUGIN_ID]
        properties = OIDCPlugin._properties
        for prop in properties:
            key = prop["id"]
            data[key] = getattr(plugin, key, "")
        return data

    def __call__(self):
        json_data = self.config_data()
        controlpanel = self.controlpanel
        context = controlpanel.context
        request = controlpanel.request
        url = context.absolute_url()
        json_schema = get_jsonschema_for_controlpanel(
            controlpanel,
            context,
            request,
        )
        response = {
            "@id": f"{url}/{SERVICE_ID}/{controlpanel.__name__}",
            "title": "OIDC settings",
            "description": "Configure OIDC connection strings",
            "group": controlpanel.group,
            "data": json_data,
            "schema": json_schema,
        }
        return response
