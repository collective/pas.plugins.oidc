import pytest
from plone import api
from pas.plugins.oidc.plugins import OIDCPlugin

@pytest.fixture()
def setup_allowed_groups(portal):
    plugin = portal.acl_users.oidc
    with api.env.adopt_roles(["Manager", "Member"]):
        plugin.allowed_groups = ["/Foundation Members"]
        plugin.user_property_as_groupid = "groups"
    yield portal
    with api.env.adopt_roles(["Manager", "Member"]):
        plugin.allowed_groups = []
        plugin.user_property_as_groupid = ""

def test_user_in_allowed_group(portal, setup_allowed_groups):
    plugin = portal.acl_users.oidc
    user = api.user.create(email="test@example.com", username="testuser")
    user.setMemberProperties(mapping={"groups": ["Foundation Members"]})
    userinfo = {"groups": ["Foundation Members"]}
    assert plugin.user_can_login(user, userinfo) is True

def test_user_not_in_allowed_group(portal, setup_allowed_groups):
    plugin = portal.acl_users.oidc
    user = api.user.create(email="test@example.com", username="testuser")
    user.setMemberProperties(mapping={"groups": ["Other Group"]})
    userinfo = {"groups": ["Other Group"]}
    assert plugin.user_can_login(user, userinfo) is False

def test_user_no_groups(portal, setup_allowed_groups):
    plugin = portal.acl_users.oidc
    user = api.user.create(email="test@example.com", username="testuser")
    user.setMemberProperties(mapping={"groups": []})
    userinfo = {"groups": []}
    assert plugin.user_can_login(user, userinfo) is False