ldapper
========

[![Build Status](https://travis-ci.org/UMIACS/ldapper.svg?branch=master)](https://travis-ci.org/UMIACS/ldapper)
[![Documentation Status](https://readthedocs.org/projects/ldapper/badge/?version=latest)](https://ldapper.readthedocs.io/en/latest/?badge=latest)

ldapper is a lightweight, expressive ORM for LDAP.

It extends the robust capabilities of python-ldap and augments it with higher-level interfaces to define your schema.  Listing and fetching all your LDAP objects is easy and straightforward.  Modifications and validation can be made with assurance using ldapper.


Requirements
------------
ldapper requires:

* Python 3.6+
* inflection

Version 0.9.0 was the last to support Python 2.

Usage
-----

```python
from ldapper.connection import BaseConnection
from ldapper.ldapnode import LDAPNode
from ldapper import fields


# define a connection
class Connection(BaseConnection):
    BASE_DN = 'dc=example,dc=com'
    URI = 'ldaps://ldap.example.com'


# define a common LDAPNode that holds the connection class you defined
class BaseModel(LDAPNode):
    connection = Connection


# define a class to represent people
class Person(BaseModel):
    uid = fields.StringField('uid', primary=True)
    uidnumber = fields.IntegerField('uidNumber')
    firstname = fields.StringField('givenName')
    lastname = fields.StringField('sn')
    email_addresses = fields.ListField('mailLocalAddress')
    photo = fields.BinaryField('jpegPhoto', optional=True)

    class Meta:
        objectclasses = ['top', 'inetOrgPerson', 'inetLocalMailRecipient']
        dn_format = 'uid=%(uid)s,ou=people'
        primary_dnprefix = 'ou=people'
        secondary_dnprefix = 'ou=people'
        identifying_attrs = ['uid']
        searchable_fields = [
'uid', 'uidNumber', 'givenName', 'sn', 'mailLocalAddress']


# use the Person class
person = Person.fetch('liam')
person.displayname = 'Chuck Yeager'
person.save()
person.delete()
```


Documentation
-------------
Available at https://ldapper.readthedocs.io/


Testing
-------
Please see the README.md file in the test directory for information on running unit tests.
