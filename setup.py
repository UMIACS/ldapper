#!/usr/bin/env python

from ldapper import __version__

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name="ldapper",
      version=__version__,
      description="UMIACS Python LDAP Interface",
      author="UMIACS Staff",
      author_email="staff@umiacs.umd.edu",
      url="https://gitlab.umiacs.umd.edu/staff/ldapper",
      license='LGPL v2.1',
      packages=["ldapper"],
      platforms="UNIX/Linux",
      classifiers=['Development Status :: 5 - Production/Stable',
                   'Operating System :: POSIX',
                   'Intended Audience :: System Administrators',
                   'Programming Language :: Python :: 2',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.6',
                   'Topic :: System :: Systems Administration :: Authentication/Directory :: LDAP', ],
      install_requires=[
          "inflection",
          "python-ldap>=2.4.15",
          "six",
      ],
      )
