# -*- coding: utf-8 -*-

from ldapper.connection import BaseConnection
from ldapper.ldapnode import LDAPNode


class Connection(BaseConnection):
    BASE_DN = 'dc=acme,dc=org'
    URI = 'ldap://localhost:389'


class MyLDAPNode(LDAPNode):
    connection = Connection
