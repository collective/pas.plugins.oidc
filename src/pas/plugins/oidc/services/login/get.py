from pas.plugins.oidc import utils
from pas.plugins.oidc.plugins import OIDCPlugin
from plone import api
from plone.restapi.services import Service
from typing import Dict
from typing import List


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
        plugins = []
        for plugin in utils.get_plugins():
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
