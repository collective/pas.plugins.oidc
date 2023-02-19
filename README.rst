.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

.. image:: https://img.shields.io/pypi/v/pas.plugins.oidc.svg
    :target: https://pypi.python.org/pypi/pas.plugins.oidc/
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/status/pas.plugins.oidc.svg
    :target: https://pypi.python.org/pypi/pas.plugins.oidc
    :alt: Egg Status

.. image:: https://img.shields.io/pypi/pyversions/pas.plugins.oidc.svg?style=plastic
    :target: https://pypi.python.org/pypi/pas.plugins.oidc/
    :alt: Supported - Python Versions

.. image:: https://img.shields.io/pypi/l/pas.plugins.oidc.svg
    :target: https://pypi.python.org/pypi/pas.plugins.oidc/
    :alt: License

.. image:: https://github.com/collective/pas.plugins.oidc/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/collective/pas.plugins.oidc/actions
    :alt: Tests

.. image:: https://coveralls.io/repos/github/collective/pas.plugins.oidc/badge.svg?branch=main
    :target: https://coveralls.io/github/collective/pas.plugins.oidc?branch=main
    :alt: Coverage


pas.plugins.oidc
================

This is an Plone authentication plugin for OpenID Connect.
OAuth 2.0 should work as well, because OpenID Connect is built on top of this protocol.

Features
--------

- PAS plugin, although currently no interfaces are activated.
- Three browser views for this PAS plugin, which are the main interaction with the outside world.


Installation
------------

Install pas.plugins.oidc by adding it to your buildout::

    [buildout]

    ...

    eggs =
        pas.plugins.oidc


and then running ``bin/buildout``


Example setup with Keycloak
---------------------------

Setup Keycloak as server
~~~~~~~~~~~~~~~~~~~~~~~~

Please refer to the `Keycloak documentation <https://www.keycloak.org/documentation>`_ for up to date instructions.
Specifically, here we will use a Docker image, so follow the instructions on how to `get started with Keycloak on Docker <https://www.keycloak.org/getting-started/getting-started-docker>`_.
This does **not** give you a production setup, but it is fine for local development.

Keycloak runs on port 8080 by default.
Plone uses the same port.
When you are reading this, you probably know how to let Plone use a different port.
So let's indeed let Keycloak use its prefered port.
At the moment of writing, this is how you start a Keycloak container::

  docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:19.0.3 start-dev

Note: when you exit this container, it still exists and you can restart it so you don't lose your configuration.
With ``docker ps -a`` figure out the name of the container and then use ``docker container start -ai <name>``.

Follow the Keycloak Docker documentation further:

* Create a realm.  Give this the name ``plone``.
* Create a user.  Remember to set a password for this user in the Credentials tab.
* Open a different browser and check that you can login to Keycloak with this user.

In the original browser, follow the steps for securing your first app.
But we will be using different settings for Plone.
And when last I checked, the actual UI differed from the documentation.
So:

* Make sure you are logged in as admin in Keycloak, and are in the Plone realm.
* Go to Clients.
* Click 'Create client':

  * client type: OpenID Connect
  * client ID: plone
  * Turn 'always display in console' on.  Useful for testing.
  * Click Next and Save.

* Now you can fill in the Access settings.  We will assume Plone runs on port 8081:

  * Root URL: http://localhost:8081/Plone/
  * Home URL: http://localhost:8081/Plone/
  * Valid redirect URIs: http://localhost:8081/Plone/acl_users/oidc/callback
  * Leave the rest at the defaults, unless you know what you are doing, and click Save.

Keycloak is ready.

Setup Plone as client
~~~~~~~~~~~~~~~~~~~~~

* In your Zope instance configuration, make sure Plone runs on port 8081.
* Make sure ``pas.plugins.openidc`` is installed with pip or Buildout.
* Start Plone and create a Plone site with id Plone.
* In the Add-ons control panel, install ``pas.plugins.openidc``.
* In the ZMI go to the plugin properties at http://localhost:8081/Plone/acl_users/oidc/manage_propertiesForm
* Set these properties:

  * OIDC/Oauth2 Issuer: http://localhost:8080/realms/plone/
  * client ID: plone.  This must match the client ID you have set in Keycloak.
  * Leave the rest at the default and save the changes.

Login
~~~~~

Go to the other browser, or logout as admin from Keycloak.
Currently, the Plone login form is unchanged.
Instead, go to the login page of the plugin: http://localhost:8081/Plone/acl_users/oidc/login
This will take you to Keycloak to login, and then return.
You should now be logged in to Plone, and see the fullname and email, if you have set this in Keycloak.


Example setup with environment variables
----------------------------------------

This plugin can be configured using environment variables instead of editing the configuration
through the ZMI.

To do so you first need to enable the feature adding an environment variabled called
`PAS_PLUGINS_OIDC_USE_ENVIRONMENT_VARS` with some value like `1`.

**When using environment variables to configure this plugin, any change made from the plugin properties page
in the ZMI will be disregarded**

Then you can create one environment variable per attribute existing in the configuration with the relevant values:

* OIDC_ISSUER = https://accounts.google.com
* OIDC_CLIENT_ID = XXXXX
* OIDC_CLIENT_SECRET = YYYYY
* OIDC_REDIRECT_URIS = https://yoursite.com/acl_users/oidc/callback
* OIDC_USE_SESSION_DATA_MANAGER = false
* OIDC_CREATE_TICKET = true
* OIDC_CREATE_RESTAPI_TICKET = true
* OIDC_CREATE_USER = true
* OIDC_SCOPE = profile,openid,email
* OIDC_USE_PKCE = true
* OIDC_USE_MODIFIED_OPENID_SCHEMA = false

Be aware that boolean values should be handled as `true` and `false` in lowercase, and the tuple values must
be set to a string separating each value with `,`.

In case you have several Plone sites in a single Zope instance, you can use your Plone site id to create
different environment variables for each Plone site.

For example if you have two Plone sites in your Zope instance
once called `Plone` and the other one called `MyShinyPlone` the environment variables can be set like this:

Plone site `Plone:`

* OIDC_ISSUER_Plone = https://accounts.google.com
* OIDC_CLIENT_ID_Plone = XXXXX
* OIDC_CLIENT_SECRET_Plone = YYYYY
* OIDC_REDIRECT_URIS_Plone = https://yoursite.com/acl_users/oidc/callback
* OIDC_USE_SESSION_DATA_MANAGER_Plone = false
* OIDC_CREATE_TICKET_Plone = true
* OIDC_CREATE_RESTAPI_TICKET_Plone = true
* OIDC_CREATE_USER_Plone = true
* OIDC_SCOPE_Plone = profile,openid,email
* OIDC_USE_PKCE_Plone = true
* OIDC_USE_MODIFIED_OPENID_SCHEMA_Plone = false

Plone site `MyShinyPlone`:

* OIDC_ISSUER_MyShinyPlone = https://my.keycloak.server.com
* OIDC_CLIENT_ID_MyShinyPlone = AAAAAA
* OIDC_CLIENT_SECRET_MyShinyPlone = BBBBB
* OIDC_REDIRECT_URIS_MyShinyPlone = https://yourothersite.com/acl_users/oidc/callback
* OIDC_USE_SESSION_DATA_MANAGER_MyShinyPlone = true
* OIDC_CREATE_TICKET_MyShinyPlone = true
* OIDC_CREATE_RESTAPI_TICKET_MyShinyPlone = true
* OIDC_CREATE_USER_MyShinyPlone = true
* OIDC_SCOPE_MyShinyPlone = profile,openid,email
* OIDC_USE_PKCE_MyShinyPlone = true
* OIDC_USE_MODIFIED_OPENID_SCHEMA_MyShinyPlone = false


Varnish
-------

If you are using the Varnish caching server in front of Plone, you may see this plugin only partially working.
Especially the ``came_from`` parameter may be ignored.
This is because the standard configuration from ``plone.recipe.varnish`` removes most cookies to improve anonymous caching.
Solution is to make sure the ``__ac_session`` cookie is added to the ``cookie-pass`` option.
Check what the current default is in the recipe, and update it::

  [varnish-configuration]
  recipe = plone.recipe.varnish:configuration
  ...
  cookie-pass = "auth_token|__ac(|_(name|password|persistent|session))=":"\.(js|css|kss)$"


Contribute
----------

- Issue Tracker: https://github.com/collective/pas.plugins.oidc/issues
- Source Code: https://github.com/collective/pas.plugins.oidc
- Documentation: https://docs.plone.org/foo/bar


References
----------

* Blog post: https://www.codesyntax.com/en/blog/log-in-in-plone-using-your-google-workspace-account

License
-------

The project is licensed under the GPLv2.
