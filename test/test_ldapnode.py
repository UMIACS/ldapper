# -*- coding: utf-8 -*-

from __future__ import absolute_import

import pytest

from ldapper.connection import BaseConnection
from ldapper.ldapnode import LDAPNode
from ldapper.fields import (
    ListField,
    StringField,
)


class connection(BaseConnection):
    BASE_DN = 'dc=acme,dc=org'
    URI = 'ldap://localhost:389'


class MyLDAPNode(LDAPNode):
    connection = connection


class Person(MyLDAPNode):
    uid = StringField('uid')
    lastname = StringField('sn')
    fullname = StringField('cn')
    addresses = ListField('mailLocalAddress', optional=True)

    class Meta:
        objectclasses = ['top', 'inetOrgPerson']
        primary = 'uid'
        rdnattr = 'uid'
        dn_format = 'uid=%(uid)s,ou=people'
        primary_dnprefix = 'ou=people'
        secondary_dnprefix = 'ou=people'
        identifying_attrs = ['uid']
        searchable_fields = ['uid', 'cn', 'displayName', 'givenName', 'sn']
        human_readable_name = 'Person'
        field_order = ['uid', 'lastname', 'fullname', 'addresses']


person_kwargs = {'uid': 'liam', 'lastname': 'Monahan', 'fullname': 'Liam Monahan'}


# TODO this should get moved somewhere more central
conn = connection.connect(logindn='cn=admin,dc=acme,dc=org',
                          password='JonSn0w')
connection.set_connection(conn)


# TODO this should also get moved somewhere else once we get further along
def get_person():
    return Person(**person_kwargs)


class TestLDAPNode:

    def test_default_meta_options(self):
        class Test(MyLDAPNode):
            pass
        assert Test._meta.objectclasses == []
        assert Test._meta.excluded_objectclasses == []
        assert Test._meta.primary is None
        assert Test._meta.rdnattr is None
        assert Test._meta.primary_dnprefix is None
        assert Test._meta.secondary_dnprefix is None
        assert Test._meta.identifying_attrs == []
        assert Test._meta.searchable_fields == []
        assert Test._meta.human_readable_name is None
        assert Test._meta.field_order is None

    def test_ldapnode_metaclass_new(self):
        """Test that the __new__ functionality of the metaclass is working."""
        assert Person.primary == 'uid'
        assert type(Person._fields['fullname']) is StringField

        # test that fields are inheritable
        class SpecialPerson(Person):
            superpower = StringField('superpower')
            lastname = StringField('sn', optional=True)
        assert 'superpower' in SpecialPerson._fields
        assert 'uid' in SpecialPerson._fields
        # lastname should be overidden in the child class
        assert SpecialPerson._fields['lastname'].optional

    def test_readonly_field(self, caplog):
        class ROPerson(Person):
            uid = StringField('uid', readonly=True)
        person = ROPerson(uid='liam', lastname='Alpert', fullname='Ram Dass')

        # cannot set
        person.uid = 'different'
        assert person.uid == 'liam'
        assert "Cannot modify read-only field 'uid'" in caplog.text

        # cannot delete
        del person.uid
        assert person.uid == 'liam'
        assert "Cannot delete read-only field 'uid'" in caplog.text

    def test_ldapnode_required_fields_present(self):
        with pytest.raises(Exception) as excinfo:
            Person()
        assert 'are missing' in str(excinfo.value)

    def test_invalid_kwargs_to_ldapnode_init(self):
        with pytest.raises(TypeError):
            Person(uid='a', lastname='l', fullname='f', invalid='foo')

    def test_ldapnode_repr(self):
        p = Person(**person_kwargs)
        assert repr(p) == 'uid=liam,ou=people,dc=acme,dc=org'

    def test_ldapnode_hash(self):
        p = Person(**person_kwargs)
        assert hash(p) == hash(p)

    def test_ldapnode_eq(self):
        p1 = Person(**person_kwargs)
        p2 = Person(**person_kwargs)
        assert not p1.__eq__(None)
        assert not p1.__eq__(True)
        assert not p1.__eq__(False)

        assert p1.__eq__(p2)
        p2.lastname = 'Caesar'
        assert not p1.__eq__(p2)

    def test_ldapnode_ordering(self):
        aaa = Person(uid='aaa', lastname='ln', fullname='fn')
        bbb = Person(uid='bbb', lastname='ln', fullname='fn')
        lst = [bbb, aaa]
        lst.sort()  # will sort by the primary attr: uid in this case
        assert lst[0] == aaa
        assert lst[1] == bbb

    def test_ldapnode_str(self):
        # this test should test differently user python 2 and python 3
        # this test is making sure that bost ListFields and other fields
        # use the dnattr when there is an LDAPNode slotted in there.
        p = Person(
            uid='liam',
            lastname=Person(**person_kwargs),
            fullname=None,
            addresses=['liam@acme.org', Person(**person_kwargs)]
        )
        expected = """DN: uid=liam,ou=people,dc=acme,dc=org
       uid: liam
  lastname: liam
 addresses: liam@acme.org
 addresses: liam"""
        assert expected == str(p)

    def test_ldapnode_dn(self):
        p = Person(**person_kwargs)

        # test that dn() works
        assert p.dn == 'uid=liam,ou=people,dc=acme,dc=org'

        # setting the dn should raise an error
        with pytest.raises(ValueError):
            p.dn = 'uid=foo'

        # test dnattr()
        assert p.dnattr() == 'liam'

        # test dnattrs()
        assert p.dnattrs() == {'uid': 'liam'}

    def test_ldapnode_create(self):
        person = Person.create(**person_kwargs)
        assert person.uid == 'liam'

    def test_fetch(self):
        p = Person(**person_kwargs)
        p.save()

        assert Person.fetch('liam') == p
        assert Person.fetch(uid='liam') == p
        assert Person.fetch(p) == p

        assert Person.fetch('who') is None

        p.delete()

    def test_happy_path_crud(self):
        person = Person(
            uid='liam',
            lastname='Monahan',
            fullname='Liam Monahan',
        )
        person.save()
        assert person.exists()
        person.delete()
        assert not person.exists()
