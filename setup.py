#!/usr/bin/env python

from ldapper import __version__

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="ldapper",
    version=__version__,
    description="LDAP ORM for Python",
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
