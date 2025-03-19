from plone import api

import pytest


@pytest.fixture()
def setup_allowed_groups(portal):
    plugin = portal.acl_users.oidc
    with api.env.adopt_roles(["Manager", "Member"]):
        plugin.allowed_groups = ["Foundation Members"]
        plugin.user_property_as_groupid = "groups"
    yield portal
    with api.env.adopt_roles(["Manager", "Member"]):
        plugin.allowed_groups = []
        plugin.user_property_as_groupid = ""


def test_user_in_allowed_group(portal, setup_allowed_groups):
    portal = setup_allowed_groups
    plugin = portal.acl_users.oidc
    userinfo = {"groups": ["Foundation Members"]}
    assert plugin.user_can_login(userinfo) is True


def test_user_not_in_allowed_group(portal, setup_allowed_groups):
    portal = setup_allowed_groups
    plugin = portal.acl_users.oidc
    userinfo = {"groups": ["Other Group"]}
    assert plugin.user_can_login(userinfo) is False


def test_user_no_groups(portal, setup_allowed_groups):
    portal = setup_allowed_groups
    plugin = portal.acl_users.oidc
    userinfo = {"groups": []}
    assert plugin.user_can_login(userinfo) is False
