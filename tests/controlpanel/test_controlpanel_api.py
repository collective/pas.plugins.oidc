import pytest


class TestControlPanel:

    @pytest.fixture(autouse=True)
    def _initialize(self, api_manager_request):
        self.api_session = api_manager_request

    @pytest.mark.parametrize(
        "key,type_",
        (
            ("@id", str),
            ("data", dict),
            ("group", str),
            ("schema", dict),
            ("title", str),
        ),
    )
    def test_serialization(self, key, type_):
        response = self.api_session.get("/@controlpanels/oidc_admin")
        data = response.json()
        assert key in data
        assert isinstance(data[key], type_)
