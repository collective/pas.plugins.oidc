# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE

# from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer

import pas.plugins.oidc


# from plone.testing import z2


class PasPluginsOidcLayer(PloneSandboxLayer):
    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        self.loadZCML(package=pas.plugins.oidc)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "pas.plugins.oidc:default")


PAS_PLUGINS_OIDC_FIXTURE = PasPluginsOidcLayer()


PAS_PLUGINS_OIDC_INTEGRATION_TESTING = IntegrationTesting(
    bases=(PAS_PLUGINS_OIDC_FIXTURE,),
    name="PasPluginsOidcLayer:IntegrationTesting",
)


PAS_PLUGINS_OIDC_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PAS_PLUGINS_OIDC_FIXTURE,),
    name="PasPluginsOidcLayer:FunctionalTesting",
)


# PAS_PLUGINS_OIDC_ACCEPTANCE_TESTING = FunctionalTesting(
#     bases=(
#         PAS_PLUGINS_OIDC_FIXTURE,
#         REMOTE_LIBRARY_BUNDLE_FIXTURE,
#         z2.ZSERVER_FIXTURE,
#     ),
#     name="PasPluginsOidcLayer:AcceptanceTesting",
# )
