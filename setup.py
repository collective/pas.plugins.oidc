"""Installer for the pas.plugins.oidc package."""

from pathlib import Path
from setuptools import find_packages
from setuptools import setup


long_description = f"""
{Path("README.md").read_text()}\n
{Path("CONTRIBUTORS.md").read_text()}\n
{Path("CHANGES.md").read_text()}\n
"""


setup(
    name="pas.plugins.oidc",
    version="2.0.0b2",
    description="OIDC support for Plone sites",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # Get more from https://pypi.org/classifiers/
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: Addon",
        "Framework :: Plone :: 6.0",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    ],
    keywords="Python Plone CMS PAS Authentication OAuth OIDC",
    author="mamico",
    author_email="mauro.amico@gmail.com",
    url="https://github.com/collective/pas.plugins.oidc",
    project_urls={
        "PyPI": "https://pypi.python.org/pypi/pas.plugins.oidc",
        "Source": "https://github.com/collective/pas.plugins.oidc",
        "Tracker": "https://github.com/collective/pas.plugins.oidc/issues",
        # 'Documentation': 'https://pas.plugins.oidc.readthedocs.io/en/latest/',
    },
    license="GPL version 2",
    packages=find_packages("src", exclude=["ez_setup"]),
    namespace_packages=["pas", "pas.plugins"],
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.8",
    install_requires=[
        "setuptools",
        "Plone",
        "Zope",
        "Products.CMFCore",
        "plone.api",
        "plone.app.registry",
        "plone.base",
        "plone.protect",
        "plone.restapi>=8.34.0",
        "oic",
        "z3c.form",
    ],
    extras_require={
        "test": [
            "zope.pytestlayer",
            "plone.app.contenttypes",
            "plone.app.testing",
            "plone.restapi[test]",
            "plone.testing",
            "pytest-cov",
            "pytest-plone>=0.2.0",
            "pytest-docker",
            "pytest-mock",
            "pytest",
            "zest.releaser[recommended]",
            "zestreleaser.towncrier",
            "pytest-mock",
            "requests-mock",
        ],
    },
    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    [console_scripts]
    update_locale = pas.plugins.oidc.locales.update:update_locale
    """,
)
