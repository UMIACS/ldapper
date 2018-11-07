Configuration
=============

To get started, you'll want to create a connection class.  It will contain the
settings necessary to connect to your LDAP.

.. code-block:: python

    from ldapper.connection import BaseConnection
   
    class Connection(BaseConnection):
        BASE_DN = 'dc=example,dc=com'
        URI = 'ldaps://ldap.example.com' 


You'll go on to create a class that all of your models can inherit from in
order to pick up on the connection settings that you want them to be backed
against.

Creating this class is not strictly necessary, but it is convenient if all of
your models are going to use the same connection.

.. code-block:: python

    from ldapper.ldapnode import LDAPNode

    class BaseModel(LDAPNode):
        connection = Connection


Create your first model:

.. code-block:: python

    from ldapper.fields import ListField, StringField

    class Person(BaseModel):
        uid = StringField('uid')
        firstname = StringField('givenName')
        lastname = StringField('sn')
        common_names = ListField('cn')


If your LDAP is anonymous, you can start using this model right away:

.. code-block:: python

    >>> for person in Person.list():
    ...     print(person.uid)
    ...
    liam
    derek
    john
