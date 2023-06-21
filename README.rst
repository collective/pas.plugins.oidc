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

Install ``pas.plugins.oidc`` by adding it to your buildout::

    [buildout]

    ...

    eggs =
        pas.plugins.oidc


and then running ``bin/buildout``

Warning
-------

Pay attention to the customization of `User info property used as userid` field, with the wrong configuration it's easy impersonate another user.

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
So let's indeed let Keycloak use its preferred port.
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
* Make sure ``pas.plugins.oidc`` is installed with pip or Buildout.
* Start Plone and create a Plone site with id Plone.
* In the Add-ons control panel, install ``pas.plugins.oidc``.
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

Usage of sessions in the login process
--------------------------------------

This plugin uses sessions during the login process to identify the user while he goes to the OIDC provider
and comes back from there.

The plugin has 2 ways of working with sessions:

- Use the Zope Session Management: if the "Use Zope session data manager" option in the plugin configuration is enabled,
the plugin will use the sessioning configuration configured in Zope. To do so we advise to use `Products.mcdutils`_
to save the session data in a memcached based storage. Otherwise Zope will try to use ZODB based sessioning
which has shown several problems in the past.

- Use the cookie based session management: if the "Use Zope session data manager" option in the plugin
configuration is disabled, the plugin will use a Cookie to save that information in the client's browser.


Settings in environment variables
---------------------------------

Instead of editing your OIDC provider settings through the ZMI, you can use `collective.regenv`_ and provide
a YAML file with your settings. This is very useful if you have different settings in different environments
and and you do not want to edit the settings each time
you move the contents.


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


.. _`collective.regenv`: https://pypi.org/project/collective.regenv/
.. _`Products.mcdutils`: https://pypi.org/project/Products.mcdutils/
