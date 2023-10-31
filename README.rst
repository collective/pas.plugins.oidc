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

This is a Plone authentication plugin for OpenID Connect.
OAuth 2.0 should work as well because OpenID Connect is built on top of this protocol.

Features
--------

- PAS plugin, although currently no interfaces are activated.
- Three browser views for this PAS plugin, which are the main interaction with the outside world.


Installation
------------

Install ``pas.plugins.oidc`` by adding it to your buildout: ::

    [buildout]

    ...

    eggs =
        pas.plugins.oidc


and then running ``bin/buildout``

Warning
-------

Pay attention to the customization of `User info property used as userid` field, with the wrong configuration it's easy to impersonate another user.


Install and configure the plugin
--------------------------------

* Go to the Add-ons control panel and install ``pas.plugins.oidc``.

* In the ZMI go to the plugin properties at http://localhost:8080/Plone/acl_users/oidc/manage_propertiesForm

* Configure the properties with the data obtained from your provider:

  * ``OIDC/Oauth2 Issuer``

  * ``Client ID``

  * ``Client secret``

  * ``redirect_uris``: this needs to match the **public URL** where the user will be redirected after the login flow is completed. It needs to include
    the `/Plone/acl_users/oidc/callback` part. When using Volto you need to expose Plone somehow to have the login process finish correctly.

  * ``Use Zope session data manager``: see the section below about the usage of session.

  * ``Create user / update user properties``: when selected the user data in Plone will be updated with the data coming from the OIDC provider.

  * ``Create authentication __ac ticket``: when selected the user will be allowed to act as a logged-in user in Plone.

  * ``Create authentication auth_token (Volto/REST API) ticket``: when selected the user will be allowed to act as a logged-in user in the Volto frontend.

  * ``Open ID scopes to request to the server``: information requested to the OIDC provider. Leave it as it is or modify it according to your provider's information.

  * ``Use PKCE``: when enabled uses PKCE_ when requesting authentication from the provider.

----

Login and Logout URLs
---------------------

When using this plugin with *Plone 6 Classic UI* the standard URLs used for login (`http://localhost:8080/Plone/login`) and logout (`http://localhost:8080/Plone/logout`)
will not trigger the usage of the plugin.

When using this plugin with a `Volto frontend <https://6.docs.plone.org/volto/index.html>`_ the standard URLs for login (`http://localhost:3000/login`)
and logout (`http://localhost:3000/logout`) will not trigger the usage of the plugin.

To login into a site using the OIDC provider, you will need to change those login URLs to the following:

* **Login URL**: /``<Plone Site Id>``/acl_users/``<oidc pas plugin id>``/login

* **Logout URL**: /``<Plone Site Id>``/acl_users/``<oidc pas plugin id>``/logout

  *Where:*

  * ``Plone Site Id``: is the id you gave to the Plone site when you created it. It is usually `Plone` but may vary. It is the last part of the URL when you browse Plone directly without using any proxy server, ex. `http://localhost:8080/Plone+` -> `Plone`.

  * ``oidc pas plugin id``: is the id you gave to the OIDC plugin when you created it inside the Plone PAS administration panel. If you just used the default configuration and installed this plugin using Plone's Add-on Control Panel, this id will be `oidc`.

When using Volto as a frontend, you need to expose those login and logout URLs somehow to make the login and logout process work.

----

Example setup with Keycloak
---------------------------

Setup Keycloak as server
~~~~~~~~~~~~~~~~~~~~~~~~

Please refer to the `Keycloak documentation <https://www.keycloak.org/documentation>`_ for up to date instructions.
Specifically, here we will use a Docker image, so follow the instructions on how to `get started with Keycloak on Docker <https://www.keycloak.org/getting-started/getting-started-docker>`_.
This does **not** give you a production setup, but it is fine for local development.

**Note:** Keycloak runs on port ``8080`` by default. Plone uses the same port. When you are reading this, you probably know how to let Plone use a different port.
So let's indeed let Keycloak use its preferred port. At the moment of writing, this is how you start a Keycloak container: ::

  docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:19.0.3 start-dev

The plugin can be used with legacy (deprecated) Keycloak ``redirect_uri`` parameter. To use this you need to enable the option
in the plugin configuration. To test that you can run the Keycloak server with the ``--spi-login-protocol-openid-connect-legacy-logout-redirect-uri=true``
option: ::

  docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:19.0.3 start-dev --spi-login-protocol-openid-connect-legacy-logout-redirect-uri=true

**Note:** when you exit this container, it still exists and you can restart it so you don't lose your configuration.
With ``docker ps -a`` figure out the name of the container and then use ``docker container start -ai <name>``.

Follow the Keycloak Docker documentation further:

* Open the `Keycloak Admin Console <http://localhost:8080/admin>`_, make sure you are logged in as ``admin``.

* Click the word ``master`` in the top-left corner, then click ``Create Realm``.

* Enter *plone* in the ``Realm name`` field.

* Click ``Create``.

* Click the word ``master`` in the top-left corner, then click ``plone``.

* Click ``Manage`` -> ``Users`` in the left-hand menu.

* Click ``Create new user``.

* Remember to set a password for this user in the ``Credentials`` tab.

* Open a different browser and check that you can login to `Keycloak Account Console <http://localhost:8080/realms/plone/account>`_ with this user.

In the original browser, follow the steps for securing your first app.
But we will be using different settings for Plone.
And when last I checked, the actual UI differed from the documentation.
So:

* Open the `Keycloak Admin Console <http://localhost:8080/admin>`_, make sure you are logged in as ``admin``.

* Click the word ``master`` in the top-left corner, then click ``plone``.

* Click ``Manage`` -> ``Clients`` in the left-hand menu.

* Click ``Create client``:

  * ``Client type``: *OpenID Connect*

  * ``Client ID``: *plone*

  * Turn ``Always display in console`` to ``On``, *Useful for testing*.

  * Click ``Next`` and click ``Save``.

* Now you can fill in the ``Settings`` -> ``Access settings``. We will assume Plone runs on port ``8081``:

  * ``Root URL``: `http://localhost:8081/Plone/`

  * ``Home URL``: `http://localhost:8081/Plone/`

  * ``Valid redirect URIs``: `http://localhost:8081/Plone*`

    **Tip:** Leave the rest at the defaults, unless you know what you are doing.

* Now you can fill in the ``Settings`` -> ``Capability config``.

  * Turn ``Client authentication`` to ``On``. This defines the type of the OIDC client. When it's ON, the
    OIDC type is set to confidential access type. When it's OFF, it is set to public access type.

  * Click ``Save``.

* Now you can access ``Credentials`` -> ``Client secret`` and click on the clipboard icon to copy it. This will
  be necessary to configure the plugin in Plone.

**Keycloak is ready done configured!**

----

Setup Plone as a client
~~~~~~~~~~~~~~~~~~~~~~~

* In your Zope instance configuration, make sure Plone runs on port 8081.

* Make sure ``pas.plugins.oidc`` is installed with `pip <https://6.docs.plone.org/glossary.html#term-pip>`_ or `Buildout <https://www.buildout.org/>`_.

* Start Plone and create a Plone site with id Plone.

* In the Add-ons control panel, install ``pas.plugins.oidc``.

* In the ZMI go to the plugin properties at http://localhost:8081/Plone/acl_users/oidc/manage_propertiesForm

* Set these properties:

  * ``OIDC/Oauth2 Issuer``: http://localhost:8080/realms/plone/

  * ``Client ID``: *plone*

    **Warning:** This property must match the ``Client ID`` you have set in Keycloak.

  * ``Client secret``: *••••••••••••••••••••••••••••••••*

    **Warning:** This property must match the ``Client secret`` you have get in Keycloak.

  * ``Use deprecated redirect_uri for logout url(/Plone/acl_users/oidc/logout)`` checked. Use this if you need to run old versions of Keycloak.

    **Tip:** Leave the rest at the defaults, unless you know what you are doing.

  * Click ``Save``.

**Plone is ready done configured!**

[TODO] screenshot.

*Warning:*

Attention, before Keycloak 18, the parameter for logout was ``redirect_uri`` and it has been deprecated since version 18. But the
Keycloak server can run with the ``redirect_uri`` if needed, it is possible to use the plugin with the legacy ``redirect_uri``
parameter enabled also. The problem is that if the deprecated parameter is enabled in the plugin but not in the server, the plugin
will not work.

So, this is the way it works:

* With legacy ``redirect_uri`` parameter enabled in Keycloak, the plugin works in default mode.

* With legacy ``redirect_uri`` parameter enabled in Keycloak, the plugin also works with legacy mode.

* With legacy ``redirect_uri`` parameter disabled in Keycloak (default after version 18), the plugin works in default mode.

* With legacy ``redirect_uri`` parameter disabled in Keycloak (default after version 18), the plugin does NOT work with legacy mode.

So, for Keycloak, it does not matter if we use the default or legacy mode if the Keycloak runs in legacy mode.

*Notes:*

* If legacy ``redirect_uri`` parameter is disabled in Keycloak, this is the default since version 18 of Keycloak according
  to this comment in *Starck Overflow*: https://stackoverflow.com/a/72142887.

* The plugin will work only if the ``Use deprecated redirect_uri for logout url(/Plone/acl_users/oidc/logout)``
  option is un-checked at the plugin properties at http://localhost:8081/Plone/acl_users/oidc/manage_propertiesForm.

----

Login
~~~~~

Go to the other browser, or logout as admin from `Keycloak Admin Console <http://localhost:8080/admin>`_.
Currently, the Plone login form is unchanged.

Instead, for testing go to the login page of the plugin: http://localhost:8081/Plone/acl_users/oidc/login,
this will take you to Keycloak to login, and then return. You should now be logged in to Plone, and see the
*full name* and *email*, if you have set this in Keycloak.

Logout
~~~~~~

If the login did work as expected you can try to Plone logout.
Currently, the Plone logout form is unchanged.

Instead, for testing go to the logout page of the plugin: http://localhost:8081/Plone/acl_users/oidc/logout,
this will take you to Keycloak to logout, and then return to the post-logout redirect URL.

----

Usage of sessions in the login process
--------------------------------------

This plugin uses sessions during the login process to identify the user while he goes to the OIDC provider
and comes back from there.

The plugin has 2 ways of working with sessions:

- Use the Zope Session Management: if the ``Use Zope session data manager`` option in the plugin configuration is enabled,
  the plugin will use the sessioning configuration configured in Zope. To do so we advise using `Products.mcdutils`_
  to save the session data in a memcached based storage. Otherwise Zope will try to use ZODB based sessioning
  which has shown several problems in the past.

- Use the cookie-based session management: if the ``Use Zope session data manager`` option in the plugin
  configuration is disabled, the plugin will use a Cookie to save that information in the client's browser.

----

Settings in environment variables
---------------------------------

Optionally, instead of editing your OIDC provider settings through the ZMI, you can use `collective.regenv`_ and provide
a ``YAML`` file with your settings. This is very useful if you have different settings in different environments
and you do not want to edit the settings each time you move the contents.

----

Varnish
-------

Optionally, if you are using the `Varnish caching server <https://6.docs.plone.org/glossary.html#term-Varnish>`_ in front
of Plone, you may see this plugin only partially working. Especially the ``came_from`` parameter may be ignored.
This is because the buildout standard configuration from `plone.recipe.varnish <https://pypi.org/project/plone.recipe.varnish/>`_
removes most cookies to improve anonymous caching.

The solution is to make sure the ``__ac_session`` cookie is added to the ``cookie-pass`` option.
Check what the current default is in the buildout recipe, and update it: ::

  [varnish-configuration]
  recipe = plone.recipe.varnish:configuration
  ...
  cookie-pass = "auth_token|__ac(|_(name|password|persistent|session))=":"\.(js|css|kss)$"

----

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
.. _PKCE: https://datatracker.ietf.org/doc/html/rfc7636