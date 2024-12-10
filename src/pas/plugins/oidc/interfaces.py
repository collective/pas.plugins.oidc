"""Module where all interfaces, events and exceptions live."""

from pas.plugins.oidc import _
from plone.restapi.controlpanels.interfaces import IControlpanel
from zope import schema
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class IPasPluginsOidcLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""


class IOIDCSettings(Interface):
    """OIDC plugin settings"""

    issuer = schema.TextLine(
        title=_("OIDC/OAuth2 Issuer"),
        description=_(""),
        required=False,
        default="",
    )
    client_id = schema.TextLine(
        title=_("Client ID"),
        description=_(""),
        required=False,
        default="",
    )
    client_secret = schema.TextLine(
        title=_("Client secret"),
        description=_(""),
        required=False,
        default="",
    )
    redirect_uris = schema.List(
        title=_("Redirect uris"),
        description=_(""),
        value_type=schema.TextLine(
            title=_("URI"),
            description=_(""),
        ),
        required=False,
        default=[],
    )
    use_session_data_manager = schema.Bool(
        title=_("Use Zope session data manager"),
        description=_(""),
        required=False,
        default=False,
    )
    create_user = schema.Bool(
        title=_("Create user / update user properties"),
        description=_(""),
        required=False,
        default=True,
    )
    create_groups = schema.Bool(
        title=_("Create groups / update group memberships"),
        description=_(""),
        required=False,
        default=False,
    )
    user_property_as_groupid = schema.TextLine(
        title=_("User info property used as groupid, default 'groups'"),
        description=_(""),
        required=False,
        default="groups",
    )
    create_ticket = schema.Bool(
        title=_("Create authentication ticket"),
        description=_("Create authentication __ac ticket"),
        required=False,
        default=True,
    )
    create_restapi_ticket = schema.Bool(
        title=_("Create restapi ticket"),
        description=_("Create authentication auth_token (volto/restapi) ticket"),
        required=False,
        default=True,
    )
    scope = schema.List(
        title=_("Open ID scopes"),
        description=_("Open ID scopes to request to the server"),
        value_type=schema.TextLine(
            title=_("Scope"),
            description=_(""),
        ),
        required=False,
        default=["profile", "email", "phone"],
    )
    use_pkce = schema.Bool(
        title=_("Use PKCE"),
        description=_(""),
        required=False,
        default=False,
    )
    use_deprecated_redirect_uri_for_logout = schema.Bool(
        title=_("Use deprecated redirect_uri"),
        description=_(
            "Use deprecated redirect_uri for logout url(/Plone/acl_users/oidc/logout)"
        ),
        required=False,
        default=False,
    )
    use_modified_openid_schema = schema.Bool(
        title=_("Use modified OpenID Schema"),
        description=_(
            "Use a modified OpenID Schema for email_verified "
            "and phone_number_verified boolean values coming as string"
        ),
        required=False,
        default=False,
    )

    user_property_as_userid = schema.TextLine(
        title=_("Property used as userid"),
        description=_("User info property used as userid, default 'sub'."),
        required=False,
        default="sub",
    )


class IOIDCControlpanel(IControlpanel):
    """OIDC Control panel"""
