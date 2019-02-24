# -*- coding: utf-8 -*-

import pytest

from .test_ldapnode import get_person

from ldapper.utils import (
    bolded,
    dn_attribute,
    strip_dn_path,
    middle_dn,
    get_attr,
    get_attrlist,
    inflect_given_cardinality,
    build_ldap_filter,
    list_items_to_sentence,
    remove_empty_strings,
    stringify,
    to_list,
    print_word_list,
)


class TestUtils(object):

    def test_bolded(self):
        assert bolded('foobar') == '\033[1mfoobar\033[0m'

    def test_dn_attribute(self):
        assert dn_attribute('cn=foo,dc=bar', 'cn') == 'foo'
        assert dn_attribute('cn=foo,cn=bar,dc=ba', 'cn') == 'foo'
        assert dn_attribute('cn=foo,dc=bar', 'uid') is None

    def test_strip_dn_path(self):
        dn = 'cn=foo,ou=groups,dc=example'
        left, right = 'cn=foo,', ',dc=example'
        assert strip_dn_path(dn) == dn
        assert strip_dn_path(dn, left=left) == 'ou=groups,dc=example'
        assert strip_dn_path(dn, right=right) == 'cn=foo,ou=groups'
        assert strip_dn_path(dn, left=left, right=right) == 'ou=groups'

    def test_middle_dn(self):
        dn = 'cn=foo,ou=middle-mgrs,ou=groups,dc=example'
        right = ',dc=example'
        assert middle_dn(dn, right) == 'ou=middle-mgrs,ou=groups'
        assert middle_dn('cn=foo', right='aaa') is None

    def test_get_attr(self):
        assert get_attr(entry={}, attr='name') is None
        assert get_attr(entry={'name': ['Liam', 'Mon']}, attr='name') == 'Liam'

    def test_get_attrlist(self):
        assert get_attrlist(entry={}, attr='name') == []
        assert get_attrlist(entry={'name': ['L', 'M']}, attr='name') == ['L', 'M']

    def test_inflect_given_cardinality(self):
        assert inflect_given_cardinality('bird', 0) == 'birds'
        assert inflect_given_cardinality('bird', 1) == 'bird'
        assert inflect_given_cardinality('bird', 2) == 'birds'

    @pytest.mark.parametrize("kwargs,expected", [
        ({'op': '&', 'attrname': 'objClass'}, '(&(objClass=foo)(objClass=bar))'),
        ({'op': '|', 'attrname': 'fooClass'}, '(|(fooClass=foo)(fooClass=bar))'),
    ])
    def test_build_ldap_filter(self, kwargs, expected):
        assert build_ldap_filter(items=['foo', 'bar'], **kwargs) == expected

    def test_build_ldap_filter_no_items(self):
        with pytest.raises(ValueError):
            assert build_ldap_filter(op='&', attrname='objectClass', items=None) == 'foo'
        with pytest.raises(ValueError):
            assert build_ldap_filter(op='&', attrname='objectClass', items=[]) == 'foo'

    def test_list_items_to_sentence(self):
        words = ['one', 'two', 'three']
        assert list_items_to_sentence(words[:1]) == 'one'
        assert list_items_to_sentence(words[:2]) == 'one and two'
        assert list_items_to_sentence(words[:3]) == 'one, two, and three'
        assert list_items_to_sentence([]) is None

    def test_print_word_list(self):
        words = [
            'one', 'two', 'three', 'four', 'five', 600, 'seven', 'eight',
            'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'foobarr', 'fourteen',
        ]
        expexcted = '''\
 one two three four five 600 seven eight nine ten eleven twelve thirteen
 foobarr fourteen'''
        assert print_word_list(words) == expexcted

    def test_remove_empty_strings(self):
        assert remove_empty_strings('foo') == 'foo'
        assert remove_empty_strings(['foo', 'bar', '', None]) == ['foo', 'bar']
        assert remove_empty_strings(False) is False
        assert remove_empty_strings('') is None

    def test_stringify(self):
        p = get_person()
        assert {'name': 'foo'} == stringify({'name': 'foo'})
        assert {'name': 'foo', 'user': p.dnattr()} == \
            stringify({'name': 'foo', 'user': p})

    def test_to_list(self):
        assert [1, 2, 3] == to_list([1, 2, 3])
        assert ["foo"] == to_list("foo")
        assert [u"foo"] == to_list(u"foo")
        assert [] == to_list(3)
