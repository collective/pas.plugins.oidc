from typing import Dict, List

from pas.plugins.oidc.plugins import OIDCPlugin
from plone import api
from plone.restapi.services import Service


class Get(Service):
    """List available login options for the site."""

    def check_permission(self):
        return True

    @staticmethod
    def list_login_providers() -> List[Dict]:
        """List all configured login providers.

        This should be moved to plone.restapi and be extendable.
        :returns: List of login options.
        """
        portal_url = api.portal.get().absolute_url()
        acl_users = api.portal.get_tool("acl_users")
        plugins = []
        for plugin in acl_users.objectValues():
            if isinstance(plugin, OIDCPlugin):
                plugins.append(
                    {
                        "id": plugin.getId(),
                        "plugin": "oidc",
                        "url": f"{portal_url}/@login-oidc/{plugin.getId()}",
                        "title": plugin.title,
                    }
                )
        return plugins

    def reply(self) -> Dict[str, List[Dict]]:
        """List login options available for the site.

        :returns: Login options information.
        """
        providers = self.list_login_providers()
        return {"options": providers}
