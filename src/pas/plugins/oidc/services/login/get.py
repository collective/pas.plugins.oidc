from pas.plugins.oidc.plugins import OIDCPlugin
from plone import api
from plone.base.interfaces import IPloneSiteRoot
from plone.restapi.interfaces import ILoginProviders
from zope.component import adapter
from zope.interface import implementer


@adapter(IPloneSiteRoot)
@implementer(ILoginProviders)
class OIDCLoginProviders:
    def __init__(self, context):
        self.context = context

    def get_providers(self):
        options = []
        acl_users = api.portal.get_tool("acl_users")
        for plugin in acl_users.objectValues():
            if isinstance(plugin, OIDCPlugin):
                url = self.context.absolute_url()
                options.append({
                    "id": plugin.getId(),
                    "plugin": "oidc",
                    "title": plugin.title,
                    "url": f"{url}/@login-oidc/{plugin.getId()}",
                })

        return options
