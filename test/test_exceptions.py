# -*- coding: utf-8 -*-

from __future__ import absolute_import

from ldapper.exceptions import (
    AddDNFailed,
    ArgumentError,
    DuplicateValue,
    NoSuchAttrValue,
    NoSuchDN,
)


class TestExceptions:

    def test_AddDNFailed(self):
        error = AddDNFailed('cn=foo,ou=bar')
        assert error.dn == 'cn=foo,ou=bar'
        assert error.msg == 'Unable to add the DN cn=foo,ou=bar to LDAP'
        assert str(error) == '(AddDNFailed) Unable to add the DN cn=foo,ou=bar to LDAP'

    def test_ArgumentError(self):
        assert ArgumentError('foo bar').msg == 'foo bar'

    def test_DuplicateValue(self):
        lst = ['wine', 'cheese', 'wine']
        error = DuplicateValue(attr='foods', value=lst)
        assert error.offending_values == ['wine']
        assert error.msg == 'Attribute "foods" has duplicate value(s): [\'wine\']'

        # maybe we already know what the duplicate values are
        error = DuplicateValue(attr='foods', value='cheese')
        assert error.msg == 'Attribute "foods" has duplicate value(s): cheese'

    def test_NoSuchAttrValue(self):
        error = NoSuchAttrValue(dn='cn=foo', attribute='dest', value='Milan')
        assert error.msg == 'DN cn=foo does not have dest Milan'

    def test_NoSuchDN(self):
        error = NoSuchDN(dn='cn=foo')
        assert error.msg == 'DN cn=foo does not exist.'
