# -*- coding: utf-8 -*-

from __future__ import absolute_import

import pytest

from ldapper.fields import (
    BinaryField,
    IntegerField,
    ListField,
    StringField,
)

from .utils import MyLDAPNode


class TestStringField:

    def test_populate(self):
        dn = 'cn=foo'
        field = StringField('name')

        # test the happy path
        assert field.populate(dn, {'name': [b'liam']}) == 'liam'

        # test if there is no entry from ldap for this field
        assert field.populate(dn, {}) is None

    def test_coerce_for_python(self):
        field = StringField('name')
        assert field.coerce_for_python(11) == '11'
        assert field.coerce_for_python('foobar') == 'foobar'

    def test_sanitize_for_ldap(self):
        field = StringField('name')
        assert field.sanitize_for_ldap(None) is None
        assert field.sanitize_for_ldap('foobar') == b'foobar'
        assert field.sanitize_for_ldap(12) == b'12'


class TestListField:

    def test_default_value(self):
        assert ListField('cns').default_value() == []

    def test_populate(self):
        dn = 'cn=foo'
        field = ListField('cn')
        assert field.populate(dn, {'cn': [b'liam', 'william']}) == ['liam', 'william']
        assert field.populate(dn, {}) == []

    def test_coerce_for_python(self):
        field = ListField('cn')
        assert field.coerce_for_python(None) == []
        assert field.coerce_for_python('foo') == ['foo']
        assert field.coerce_for_python(['foo']) == ['foo']

    def test_sanitize_for_ldap(self):
        field = ListField('cn')
        assert field.sanitize_for_ldap(['foo', 'bar']) == [b'foo', b'bar']


class TestIntegerField:

    def test_populate(self):
        field = IntegerField('id')
        assert field.populate('cn=foo', {'id': [b'12']}) == '12'
        assert field.populate('cn=foo', {}) is None

    def test_coerce_for_python_required(self):
        field = IntegerField('id')
        assert field.coerce_for_python('11') == 11
        with pytest.raises(ValueError):
            field.coerce_for_python('foo')
        with pytest.raises(ValueError):
            field.coerce_for_python(None)

    def test_coerce_for_python_optional(self):
        field = IntegerField('id', optional=True)
        assert field.coerce_for_python('11') == 11

        # None is ok, but values that truly don't parse will still fail
        assert field.coerce_for_python(None) is None
        with pytest.raises(ValueError):
            field.coerce_for_python('foo')

    def test_sanitize_for_ldap(self):
        field = IntegerField('id')
        assert field.sanitize_for_ldap(11) == b'11'
        assert field.sanitize_for_ldap(None) is None


class TestBinaryField:

    def test_binary_field_pretty_print(self):
        class Foo(MyLDAPNode):
            photo = BinaryField('photo')
            name = StringField('name')

            class Meta:
                dn_format = 'ou=foos'

        obj = Foo(photo=b'aaa', name='foobar')
        obj.date_created = '2018'
        obj.date_modified = '2018'
        obj.user_created = '2018'
        obj.user_modified = '2018'

        output = obj.pretty_print()

        assert 'photo' in output
        assert 'Binary (3 bytes)' in output
        assert 'aaa' not in output
        assert 'name' in output

    def test_coerce_for_python(self):
        field = BinaryField('photo')
        assert field.coerce_for_python(b'aaa') == b'aaa'