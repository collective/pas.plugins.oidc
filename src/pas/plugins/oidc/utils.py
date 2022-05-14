from oic.oauth2.message import ParamDefinition
from oic.oauth2.message import SINGLE_OPTIONAL_INT
from oic.oauth2.message import SINGLE_OPTIONAL_STRING
from oic.oauth2.message import SINGLE_REQUIRED_STRING
from oic.oic.message import OpenIDSchema
from oic.oic.message import OPTIONAL_ADDRESS
from oic.oic.message import OPTIONAL_MESSAGE
# from oic.oic.message import SINGLE_OPTIONAL_BOOLEAN


PLUGIN_ID = "oidc"


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
SINGLE_OPTIONAL_BOOLEAN_AS_STRING = ParamDefinition(
    str, False, boolean_string_ser, boolean_string_deser, False
)


class CustomOpenIDNonBooleanSchema(OpenIDSchema):
    c_param = {
        "sub": SINGLE_REQUIRED_STRING,
        "name": SINGLE_OPTIONAL_STRING,
        "given_name": SINGLE_OPTIONAL_STRING,
        "family_name": SINGLE_OPTIONAL_STRING,
        "middle_name": SINGLE_OPTIONAL_STRING,
        "nickname": SINGLE_OPTIONAL_STRING,
        "preferred_username": SINGLE_OPTIONAL_STRING,
        "profile": SINGLE_OPTIONAL_STRING,
        "picture": SINGLE_OPTIONAL_STRING,
        "website": SINGLE_OPTIONAL_STRING,
        "email": SINGLE_OPTIONAL_STRING,
        "email_verified": SINGLE_OPTIONAL_BOOLEAN_AS_STRING,
        "gender": SINGLE_OPTIONAL_STRING,
        "birthdate": SINGLE_OPTIONAL_STRING,
        "zoneinfo": SINGLE_OPTIONAL_STRING,
        "locale": SINGLE_OPTIONAL_STRING,
        "phone_number": SINGLE_OPTIONAL_STRING,
        "phone_number_verified": SINGLE_OPTIONAL_BOOLEAN_AS_STRING,
        "address": OPTIONAL_ADDRESS,
        "updated_at": SINGLE_OPTIONAL_INT,
        "_claim_names": OPTIONAL_MESSAGE,
        "_claim_sources": OPTIONAL_MESSAGE,
    }
