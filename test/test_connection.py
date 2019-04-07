# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import Connection


class TestConnection:

    def test_connection_init(self):
        conn = Connection(logindn=None, password=None, basedn='foo')
        assert conn.basedn == 'foo'

        uri = 'ldap://127.0.0.1:389'
        conn = Connection(logindn=None, password=None, uri=uri)
        assert conn.uri == uri

    def test_connnection_connect_failed_attempt(self, caplog):
        conn = Connection.connect(logindn='foo', password='wrong',
                                  retries=1, uri='ldap://localhost:389')
        assert conn is None

        assert 'login attempt 1 failed' in caplog.text

    def test_connection_is_anonymous(self):
        conn = Connection.connect_anon()
        assert conn.is_anonymous()
        assert conn.whoami() is None
        assert conn.whoami_short() is None

    def test_connection_fully_qualify_dn(self):
        conn = Connection.connect_anon()

        uid = 'user'
        dn = 'uid=user,ou=people,dc=acme,dc=org'

        # a shortname is transformed into a fully qualified dn
        assert conn._fully_qualify_dn(logindn=uid) == dn

        # an already fully qualified dn is left unchanged
        assert conn._fully_qualify_dn(logindn=dn) == dn

    def test_connection_str(self, connection):
        expected = 'ldap://localhost:389 as cn=admin,dc=acme,dc=org'
        assert str(connection) == expected
        assert unicode(connection) == expected

    def test_connection_whoami(self, connection):
        assert connection.whoami() == 'cn=admin,dc=acme,dc=org'
        assert connection.whoami_short() == 'admin'