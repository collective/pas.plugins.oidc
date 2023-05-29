Using the development buildout
==============================

Create a virtualenv in the package::

    $ virtualenv --clear .

Install requirements with pip::

    $ ./bin/pip install -r requirements.txt

Run buildout::

    $ ./bin/buildout

Start Plone in foreground:

    $ ./bin/instance fg


Running tests
-------------

    $ tox

list all tox environments:

    $ tox -l
    plone52-py37
    plone52-py38
    plone52-py39
    plone60-py37
    plone60-py38
    plone60-py39
    plone60-py310
    plone60-py311


run a specific tox env:

    $ tox -e plone52-py37

