#!/usr/bin/env python

from ldapper import __version__

from os import path

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

BASE_DIR = path.abspath(path.dirname(__file__))
with open(path.join(BASE_DIR, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="ldapper",
    version=__version__,
    description="LDAP ORM for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Liam Monahan",
    author_email="liam@liammonahan.com",
    url="https://github.com/UMIACS/ldapper",
    license="LGPL v2.1",
    packages=["ldapper"],
    platforms="UNIX/Linux",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Database",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration :: Authentication/Directory :: LDAP",
    ],
    install_requires=["inflection", "python-ldap>=2.4.15"],
)
