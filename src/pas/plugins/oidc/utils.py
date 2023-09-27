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


from json import dumps

try:
    from urllib import urlencode, unquote
    from urlparse import urlparse, parse_qsl, ParseResult
except ImportError:
    # Python 3 fallback
    from urllib.parse import (
        urlencode,
        unquote,
        urlparse,
        parse_qsl,
        ParseResult,
    )


def add_url_params(url, params):
    """Add GET params to provided URL being aware of existing.

    :param url: string of target URL
    :param params: dict containing requested params to be added
    :return: string with updated URL

    >> url = 'https://stackoverflow.com/test?answers=true'
    >> new_params = {'answers': False, 'data': ['some','values']}
    >> add_url_params(url, new_params)
    'https://stackoverflow.com/test?data=some&data=values&answers=false'
    """
    # Unquoting URL first so we don't lose existing args
    url = unquote(url)
    # Extracting url info
    parsed_url = urlparse(url)
    # Extracting URL arguments from parsed URL
    get_args = parsed_url.query
    # Converting URL arguments to dict
    parsed_get_args = dict(parse_qsl(get_args))
    # Merging URL arguments dict with new params
    parsed_get_args.update(params)

    # Bool and Dict values should be converted to json-friendly values
    # you may throw this part away if you don't like it :)
    parsed_get_args.update(
        {
            k: dumps(v)
            for k, v in parsed_get_args.items()
            if isinstance(v, (bool, dict))
        }
    )

    # Converting URL argument to proper query string
    encoded_get_args = urlencode(parsed_get_args, doseq=True)
    # Creating new parsed result object based on provided with new
    # URL arguments. Same thing happens inside urlparse.
    new_url = ParseResult(
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        encoded_get_args,
        parsed_url.fragment,
    ).geturl()

    return new_url
