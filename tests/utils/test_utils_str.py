from pas.plugins.oidc import utils

import pytest


class TestUtilsBooleanSer:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, False),
            ("0", True),
            ("", False),
            (1, True),
            (False, False),
            (True, True),
        ],
    )
    def test_boolean_string_ser(self, value, expected):
        func = utils.boolean_string_ser
        assert func(value) is expected


class TestUtilsBooleanDeSer:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (False, False),
            ("true", True),
            ("false", False),
            (True, True),
        ],
    )
    def test_boolean_string_deser(self, value, expected):
        func = utils.boolean_string_deser
        assert func(value) is expected
