from hashlib import sha256
from oic import rndstr
from oic.exception import RequestError
from oic.oic import message
from pas.plugins.oidc import logger
from pas.plugins.oidc import plugins
from pas.plugins.oidc.plugins import OIDCPlugin
from pas.plugins.oidc.session import Session
from plone import api
from typing import Union

import base64
import re


def boolean_string_ser(val, sformat=None, lev=0):
    bool_value = bool(val)
    return bool_value


def boolean_string_deser(val, sformat=None, lev=0):
    if isinstance(val, bool):
        return val
    else:
        if val.lower() == "true":
            return True

    return False


# value type, required, serializer, deserializer, null value allowed
SINGLE_OPTIONAL_BOOLEAN_AS_STRING = message.ParamDefinition(
    str, False, boolean_string_ser, boolean_string_deser, False
)


class CustomOpenIDNonBooleanSchema(message.OpenIDSchema):
    c_param = {
        "sub": message.SINGLE_REQUIRED_STRING,
        "name": message.SINGLE_OPTIONAL_STRING,
        "given_name": message.SINGLE_OPTIONAL_STRING,
        "family_name": message.SINGLE_OPTIONAL_STRING,
        "middle_name": message.SINGLE_OPTIONAL_STRING,
        "nickname": message.SINGLE_OPTIONAL_STRING,
        "preferred_username": message.SINGLE_OPTIONAL_STRING,
        "profile": message.SINGLE_OPTIONAL_STRING,
        "picture": message.SINGLE_OPTIONAL_STRING,
        "website": message.SINGLE_OPTIONAL_STRING,
        "email": message.SINGLE_OPTIONAL_STRING,
        "email_verified": SINGLE_OPTIONAL_BOOLEAN_AS_STRING,
        "gender": message.SINGLE_OPTIONAL_STRING,
        "birthdate": message.SINGLE_OPTIONAL_STRING,
        "zoneinfo": message.SINGLE_OPTIONAL_STRING,
        "locale": message.SINGLE_OPTIONAL_STRING,
        "phone_number": message.SINGLE_OPTIONAL_STRING,
        "phone_number_verified": SINGLE_OPTIONAL_BOOLEAN_AS_STRING,
        "address": message.OPTIONAL_ADDRESS,
        "updated_at": message.SINGLE_OPTIONAL_INT,
        "_claim_names": message.OPTIONAL_MESSAGE,
        "_claim_sources": message.OPTIONAL_MESSAGE,
    }


_URL_MAPPING = (
    (r"(.*)/api($|/.*)", r"\1\2"),
    (r"(.*)/\+\+api\+\+($|/.*)", r"\1\2"),
)


def url_cleanup(url: str) -> str:
    """Clean up redirection url."""
    # Volto frontend mapping exception
    for search, replace in _URL_MAPPING:
        match = re.search(search, url)
        if match:
            url = re.sub(search, replace, url)
    return url


def get_plugins() -> list:
    """Return all OIDC plugins for the current portal."""
    pas = api.portal.get_tool("acl_users")
    plugins_to_return = []
    for plugin in pas.objectValues():
        if isinstance(plugin, OIDCPlugin):
            plugins_to_return.append(plugin)

    return plugins_to_return


# Flow: Start
def initialize_session(plugin: plugins.OIDCPlugin, request) -> Session:
    """Initialize a Session."""
    use_session_data_manager: bool = plugin.getProperty("use_session_data_manager")
    use_pkce: bool = plugin.getProperty("use_pkce")
    session = Session(request, use_session_data_manager)
    # state is used to keep track of responses to outstanding requests (state).
    # nonce is a string value used to associate a Client session with an ID Token, and to mitigate replay attacks.
    session.set("state", rndstr())
    session.set("nonce", rndstr())
    came_from = request.get("came_from")
    if came_from:
        session.set("came_from", came_from)
    if use_pkce:
        session.set("verifier", rndstr(128))
    return session


def pkce_code_verifier_challenge(value: str) -> str:
    """Build a sha256 hash of the base64 encoded value of value

    Be careful: this should be url-safe base64 and we should also remove the trailing '='
    See https://www.stefaanlippens.net/oauth-code-flow-pkce.html#PKCE-code-verifier-and-challenge
    """
    hash_code = sha256(value.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(hash_code).decode("utf-8").replace("=", "")


def authorization_flow_args(plugin: plugins.OIDCPlugin, session: Session) -> dict:
    """Return the arguments used for the authorization flow."""
    # https://pyoidc.readthedocs.io/en/latest/examples/rp.html#authorization-code-flow
    args = {
        "client_id": plugin.getProperty("client_id"),
        "response_type": "code",
        "scope": plugin.get_scopes(),
        "state": session.get("state"),
        "nonce": session.get("nonce"),
        "redirect_uri": plugin.get_redirect_uris(),
    }
    if plugin.getProperty("use_pkce"):
        # Build a random string of 43 to 128 characters
        # and send it in the request as a base64-encoded urlsafe string of the sha256 hash of that string
        args["code_challenge"] = pkce_code_verifier_challenge(session.get("verifier"))
        args["code_challenge_method"] = "S256"
    return args


# Flow: Process
def load_existing_session(plugin: plugins.OIDCPlugin, request) -> Session:
    use_session_data_manager: bool = plugin.getProperty("use_session_data_manager")
    session = Session(request, use_session_data_manager)
    return session


def parse_authorization_response(
    plugin: plugins.OIDCPlugin, qs: str, client, session: Session
) -> tuple:
    """Parse a flow response and return arguments for client calls."""
    use_pkce: bool = plugin.getProperty("use_pkce")
    aresp = client.parse_response(
        message.AuthorizationResponse, info=qs, sformat="urlencoded"
    )
    aresp_state = aresp["state"]
    session_state = session.get("state")
    if aresp_state != session_state:
        logger.error(
            f"Invalid OAuth2 state response: {aresp_state}" f"session: {session_state}"
        )
        # TODO: need to double check before removing the comment below
        # raise ValueError("invalid OAuth2 state")

    args = {
        "code": aresp["code"],
        "redirect_uri": plugin.get_redirect_uris(),
    }

    if use_pkce:
        args["code_verifier"] = session.get("verifier")
    return args, aresp["state"]


def get_user_info(client, state, args) -> Union[message.OpenIDSchema, dict]:
    resp = client.do_access_token_request(
        state=state,
        request_args=args,
        authn_method="client_secret_basic",
    )
    user_info = {}
    if isinstance(resp, message.AccessTokenResponse):
        # If it's an AccessTokenResponse the information in the response will be stored in the
        # client instance with state as the key for future use.
        user_info = resp.to_dict().get("id_token", {})
        if client.userinfo_endpoint:
            # https://openid.net/specs/openid-connect-core-1_0.html#UserInfo

            # XXX: Not completely sure if this is even needed
            #      We do not have a OpenID connect provider with userinfo endpoint
            #      enabled and with the weird treatment of boolean values, so we cannot test this
            # if self.context.getProperty("use_modified_openid_schema"):
            #     userinfo = client.do_user_info_request(state=aresp["state"], user_info_schema=CustomOpenIDNonBooleanSchema)
            # else:
            #     userinfo = client.do_user_info_request(state=aresp["state"])
            try:
                user_info = client.do_user_info_request(state=state)
            except RequestError as exc:
                logger.error(
                    "Authentication failed, probably missing openid scope",
                    exc_info=exc,
                )
                user_info = {}
        # userinfo in an instance of OpenIDSchema or ErrorResponse
        # It could also be dict, if there is no userinfo_endpoint
        if not (user_info and isinstance(user_info, (message.OpenIDSchema, dict))):
            logger.error(f"Authentication failed,  invalid response {resp} {user_info}")
            user_info = {}
    elif isinstance(resp, message.TokenErrorResponse):
        logger.error(f"Token error response: {resp.to_json()}")
    else:
        logger.error(f"Authentication failed {resp}")
    return user_info


def process_came_from(session: Session, came_from: str = "") -> str:
    if not came_from:
        came_from = session.get("came_from")
    portal_url = api.portal.get_tool("portal_url")
    if not (came_from and portal_url.isURLInPortal(came_from)):
        came_from = api.portal.get().absolute_url()
    return url_cleanup(came_from)
