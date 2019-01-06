# -*- coding: utf-8 -*-

from ldapper.utils import (
    dn_attribute,
    strip_dn_path,
    middle_dn,
    inflect_given_cardinality,
    list_items_to_sentence,
    remove_empty_strings,
)


class TestUtils(object):

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

    def test_inflect_given_cardinality(self):
        assert inflect_given_cardinality('bird', 0) == 'birds'
        assert inflect_given_cardinality('bird', 1) == 'bird'
        assert inflect_given_cardinality('bird', 2) == 'birds'

    def test_list_items_to_sentence(self):
        words = ['one', 'two', 'three']
        assert list_items_to_sentence(words[:1]) == 'one'
        assert list_items_to_sentence(words[:2]) == 'one and two'
        assert list_items_to_sentence(words[:3]) == 'one, two, and three'
        assert list_items_to_sentence([]) is None

    def test_remove_empty_strings(self):
        assert remove_empty_strings('foo') == 'foo'
        assert remove_empty_strings(['foo', 'bar', '', None]) == ['foo', 'bar']
        assert remove_empty_strings(False) is False
        assert remove_empty_strings('') is None
