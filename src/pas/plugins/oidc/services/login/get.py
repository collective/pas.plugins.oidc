# -*- coding: utf-8 -*-
from pas.plugins.oidc.plugins import OIDCPlugin
from plone import api
from plone.base.interfaces import IPloneSiteRoot
from plone.restapi.interfaces import IExternalLoginProviders
from zope.component import adapter
from zope.interface import implementer


@adapter(IPloneSiteRoot)
@implementer(IExternalLoginProviders)
class OIDCLoginProviders:
    def __init__(self, context):
        self.context = context

    def get_providers(self):
        options = []
        acl_users = api.portal.get_tool("acl_users")
        for plugin in acl_users.objectValues():
            if isinstance(plugin, OIDCPlugin):
                options.append(
                    {
                        "id": plugin.getId(),
                        "plugin": "authomatic",
                        "title": plugin.title,
                        "url": f"{self.context.absolute_url()}/@login-oidc/${plugin.getId()}",
                    }
                )

        return {"options": options}
