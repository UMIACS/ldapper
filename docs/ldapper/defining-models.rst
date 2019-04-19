.. _models-and-fields:

Defining Models and Fields
==========================

Models
------

You will define all of your different kinds of objects using
:class:`~ldapper.ldapnode.LDAPNode`.  An ``LDAPNode`` models LDAP objects that
must be composed of at least two ``objectClasses``.

Let us imagine that we are trying to represent the people objects in our
directory.  We will define a ``Person`` class.  Our Person will contain a
:class:`~ldapper.fields.Field` for each attribute that a Person has.

.. code-block:: python

    from ldapper import fields
    from ldapper.ldapnode import LDAPNode

    class BaseModel(LDAPNode):
        connection = Connection

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

Model definition uses the declaritive syntax seen in other popular ORMs like
SQLAlchemy, Django, or Peewee.

.. note::
   The ``Person`` gets its connection to your LDAP through the ``connection``
   defined on the ``BaseModel``.

Fields
------

Notice that there are many different field types available to you.  All fields 
are subclasses of :class:`ldapper.fields.Field` and know how to serialize into
and out of LDAP.

All fields accept one mandatory argument: the name of the attribute in LDAP.

Fields are required by default.  You can pass ``optional=True`` to the field
constructor to make it optional, as is the case for the ``photo`` attribute.

In the next section we will use our newly-created ``Person``.
