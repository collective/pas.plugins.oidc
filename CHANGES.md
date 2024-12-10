# Changelog

<!--
   You should *NOT* be adding new change log entries to this file.
   You should create a file in the news directory instead.
   For helpful instructions, please see:
   https://github.com/plone/plone.releaser/blob/master/ADD-A-NEWS-ITEM.rst
-->

<!-- towncrier release notes start -->

## 2.0.0b2 (2024-12-09)


### New features:

- Update the Deutsch translation [macagua] [#60](https://github.com/collective/pas.plugins.oidc/issues/60)
- Implement control panel to configure pas.plugins.oidc [@ericof] [#65](https://github.com/collective/pas.plugins.oidc/issues/65)


### Documentation:

- Fixed port numbers on README file [macagua] [#51](https://github.com/collective/pas.plugins.oidc/issues/51)


## 2.0.0b1 (2024-06-25)


### New features:

- Added Deutsch translation
  [@macagua] [#45](https://github.com/collective/pas.plugins.oidc/issues/45)
- Allow multiple instances of OIDC plugin in a given Plone site @erral [#48](https://github.com/collective/pas.plugins.oidc/issues/48)
- Notify user events on creation and authentication. [@Arkusm][@ericof] [#53](https://github.com/collective/pas.plugins.oidc/issues/53)
- Updated the latest .po templates for translate
  Updated Spanish translation
  [@macagua] [#55](https://github.com/collective/pas.plugins.oidc/issues/55)


### Internal:

- Update configuration files @plone 


### Documentation:

- Recommend using `[pas.plugins.keycloakgroups](https://pypi.org/project/pas.plugins.keycloakgroups/)` for groups support with Keycloak [@ericof] [#42](https://github.com/collective/pas.plugins.oidc/issues/42)


## 2.0.0a1 (2023-11-23)


### New features:

- Implement [plone/meta](https://github.com/plone/meta) and convert documentation to Markdown [@ericof] [#32](https://github.com/collective/pas.plugins.oidc/issues/32)
- Drop support to Python 2.7 and Plone 5.2 [@ericof] [#33](https://github.com/collective/pas.plugins.oidc/issues/33)
- Implement restapi services to handle authentication flow [@ericof] [#38](https://github.com/collective/pas.plugins.oidc/issues/38)


### Internal:

- Rewrite tests from unittest to pytest with [pytest-plone](https://pypi.org/project/pytest-plone/) [@ericof] [#34](https://github.com/collective/pas.plugins.oidc/issues/34)
- Allow dict instances to hold userinfo [@erral] [#35](https://github.com/collective/pas.plugins.oidc/issues/35)
- Declare the minimum requirements for Plone/python in the readme [mamico] [#36](https://github.com/collective/pas.plugins.oidc/issues/36)


## 1.0.0 (2023-11-11)

- Allow dict instances to hold userinfo [@erral]

## 1.0a6 (2023-07-20)

- Added Spanish translation [@macagua]

- Added improvements about i18n support [macagua]

- Drop python 2.7 and Plone 4 support [@erral]

- Add support for the post_logout parameter for logout api. [@ramiroluz]


## 1.0a5 (2023-04-05)

- Catch exceptions during the OAuth process [@erral]

- Update the plugin to make challenges.
  An anonymous user who visits a page for which you have to be authenticated,
  is redirected to the new require_login view on the plugin.
  This works the same way as the standard require_login page of Plone.
  [@maurits]

- Add a property for the default userinfo instead of using only sub. [@eikichi18]


## 1.0a4 (2023-01-16)

- Call getProperty only once when getting redirect_uris or scope. [@maurits]

- use getProperty accessor [@mamico]


## 1.0a3 (2022-10-30)

- Removed the hardcoded auth cookie name [@alecghica]

- Fixed Python compatibility with version >= 3.6 [@alecghica]

- check if url is in portal before redirect #2 [@erral]

- manage came_from [@mamico]

## 1.0a2 (unreleased)

- do userinforequest if there is a client.userinfo_endpoint [@mamico]

## 1.0a1 (unreleased)

- Initial release. [@mamico]
