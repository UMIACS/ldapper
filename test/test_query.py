# -*- coding: utf-8 -*-

import pytest

from ldapper.fields import StringField
from ldapper.query import Q

from .utils import MyLDAPNode


class Person(MyLDAPNode):
    uid = StringField('uid', primary=True)
    firstname = StringField('givenName', optional=True)
    lastname = StringField('sn', optional=True)


class TestQ:

    def test_one_condition(self):
        assert Q(firstname='Liam').compile(Person) == '(givenName=Liam)'

    def test_or_conditions(self):
        qset = Q(firstname='Liam') | Q(lastname='Monahan')
        assert qset.compile(Person) == '(|(givenName=Liam)(sn=Monahan))'

    def test_or_conditions_same_attr(self):
        qset = Q(firstname='Liam') | Q(firstname='Bob')
        assert qset.compile(Person) == '(|(givenName=Liam)(givenName=Bob))'

    def test_and_conditions(self):
        qset = Q(firstname='Liam') & Q(lastname='Monahan')
        assert qset.compile(Person) == '(&(givenName=Liam)(sn=Monahan))'

    def test_complex_conditions(self):
        qset = (Q(firstname='Alice') | Q(firstname='Bob')) & Q(uid='liam')
        assert qset.compile(Person) == '(&(|(givenName=Alice)(givenName=Bob))(uid=liam))'

    def test_complex_conditions2(self):
        qset = (
            (Q(firstname='Alice') | Q(firstname='Bob')) &
            (Q(uid='liam') | Q(uid='derek'))
        )
        assert qset.compile(
            Person) == '(&(|(givenName=Alice)(givenName=Bob))(|(uid=liam)(uid=derek)))'

    def test_complex_conditions3(self):
        # Test that And() & And() doesn't nest more than it needs to.
        # Same goes for Or() | Or().
        qset = (Q(lastname='Lennon') & Q(lastname='McCartney')) & (
            Q(lastname='Harrison') & Q(lastname='Starr'))
        assert qset.compile(
            Person) == '(&(sn=Lennon)(sn=McCartney)(sn=Harrison)(sn=Starr))'

        qset = (Q(lastname='Lennon') | Q(lastname='McCartney')) | (
            Q(lastname='Harrison') | Q(lastname='Starr'))
        assert qset.compile(
            Person) == '(|(sn=Lennon)(sn=McCartney)(sn=Harrison)(sn=Starr))'

    def test_complex_conditions4(self):
        qset = (Q(lastname='Lennon') & Q(lastname='McCartney')) & \
            Q(firstname='Ringo', lastname='Starr')
        assert qset.compile(
            Person) == '(&(sn=Lennon)(sn=McCartney)(givenName=Ringo)(sn=Starr))'

        qset = (Q(lastname='Lennon') | Q(lastname='McCartney')) | \
            Q(firstname='Ringo', lastname='Starr')
        assert qset.compile(
            Person) == '(|(sn=Lennon)(sn=McCartney)(&(givenName=Ringo)(sn=Starr)))'

    def test_deeply_nested(self):
        qset = (
            Q(firstname='Liam') &
            (Q(lastname='Smith') | (
                Q(uid='liam') & Q(lastname='Monahan')
            ))
        )
        assert qset.compile(
            Person) == '(&(givenName=Liam)(|(sn=Smith)(&(uid=liam)(sn=Monahan))))'

    def test_deeply_nested2(self):
        qset = (
            Q(firstname='Liam') |
            (Q(lastname='Smith') & (
                Q(uid='liam') & Q(lastname='Monahan')
            ))
        )
        assert qset.compile(Person) == \
            '(|(givenName=Liam)(&(sn=Smith)(uid=liam)(sn=Monahan)))'

        qset = Q(firstname='Liam') | (Q(lastname='Smith') | Q(uid='liam'))
        assert qset.compile(Person) == \
            '(|(givenName=Liam)(sn=Smith)(uid=liam))'

    def test_deeply_nested3(self):
        qset = (Q(uid='liam') & Q(lastname='Monahan') & Q(firstname='Liam'))
        assert qset.compile(
            Person) == '(&(uid=liam)(sn=Monahan)(givenName=Liam))'

        qset = (Q(uid='liam') | Q(lastname='Monahan') | Q(firstname='Liam'))
        assert qset.compile(
            Person) == '(|(uid=liam)(sn=Monahan)(givenName=Liam))'

        qset = (
            Q(firstname='Liam') |
            (Q(lastname='Smith') & (
                Q(uid='liam') & Q(lastname='Monahan') & Q(firstname='Liam')
            ))
        )
        assert qset.compile(Person) == \
            '(|(givenName=Liam)(&(sn=Smith)(uid=liam)(sn=Monahan)(givenName=Liam)))'

    def test_multi_condition(self):
        qset = Q(firstname='Liam', lastname='Monahan', uid='liam')
        assert qset.compile(Person) == '(&(givenName=Liam)(sn=Monahan)(uid=liam))'

        qset = Q(firstname='Liam', lastname='Monahan') | Q(uid='liam')
        assert qset.compile(Person) == '(|(&(givenName=Liam)(sn=Monahan))(uid=liam))'

    def test_attribute_misspelling(self):
        with pytest.raises(AttributeError):
            Q(missingattr='foo').compile(Person)

    def test_wrong_type(self):
        with pytest.raises(TypeError):
            Q(foo='bar') & 'foobar'
        with pytest.raises(TypeError):
            Q(foo='bar') | 'foobar'
