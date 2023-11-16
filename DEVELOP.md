## Local Development

You need a working `python` environment (system, `virtualenv`, `pyenv`, etc) version 3.8 or superior.

Then install the dependencies and a development instance using:

```bash
make build
```

### Start Local Server

Start Plone, on port 8080, with the command:

```bash
make start
```

#### Keycloak

The `pas.plugins.oidc` repository has a working setup for a `Keycloak` development server using `Docker` and `Docker Compose`. To use it, in a terminal, run the command:

```bash
make keycloak-start
```

There are two realms configured `plone` and `plone-test`. The later is used in automated tests, while the former should be used for your development environment.

The `plone` realm ships with an user that has the following credentials:

* username: **user**
* password: **12345678**

To stop a running `Keycloak` (needed when running tests), use:

```bash
make keycloak-stop
```

### Update translations

```bash
make i18n
```

### Format codebase

```bash
make format
```

### Run tests

Testing of this package is done with [`pytest`](https://docs.pytest.org/) and [`tox`](https://tox.wiki/).

Run all tests with:

```bash
make test
```

Run all tests but stop on the first error and open a `pdb` session:

```bash
./bin/tox -e test -- -x --pdb
```

Run tests named `TestServiceOIDCPost`:

```bash
./bin/tox -e test -- -k TestServiceOIDCPost
```
