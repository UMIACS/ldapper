.. _crud-operations:

The CRUD Operations
===================

This section will make use of the ``Person`` class we defined in the previous
section.

Create
------

.. code-block:: python

   person = Person(
      uid='cnorris',
      uidnumber=1337,
      firstname='Chuck',
      lastname='Norris',
      email_addresses=[
          'chuck@example.com',
          'cnorris@megacorp.com',
      ],
   )

We've now created a person, but not yet saved it.  We can check if the object
:func:`~ldapper.ldapnode.LDAPNode.exists` or has been saved:

.. code-block:: python

   >>> person.exists()
   False

This will query the ldap and look to see if there is something with the DN of
this object present.

Let's go and save our person.

.. code-block:: python

   >>> person.save()
   >>> person.exists()
   True

Read
----

Tomorrow we come back and want to look up Chuck Norris's LDAP entry.
First we will need to fetch him.

.. code-block:: python

   >>> chuck = Person.fetch('cnorris')
   >>> print(chuck)
   DN: uid=cnorris,ou=people,dc=umiacs,dc=umd,dc=edu
               uid: cnorris
         firstname: Chuck
          lastname: Norris 
         uidnumber: 1337
   email_addresses: chuck@example.com
   email_addresses: cnorris@megacorp.com

If we wanted to get all of our people, we can use
:func:`~ldapper.ldapnode.LDAPNode.list`.

.. code-block:: python

   >>> people = Person.list()
   >>> people
   [uid=liam,ou=people,dc=umiacs,dc=umd,dc=edu,
    uid=cnorris,ou=people,dc=umiacs,dc=umd,dc=edu]

Notice that the ``__repr__`` is set to use the DN of the object.

Update
------

In order to make updates to the LDAP, we will need to authenticate.

.. code-block:: python

   >>> conn = Connection.connect()
   Enter a LDAP loginDN or username: liam
   Password for LDAP (liam):
   >>> Connection.set_connection(conn)

.. note::

   An object will use the connection object that was set at the time that it
   was instantiated.  Subsequent changes to the set, static connection will
   not affect the connection being used by existing objects.

.. code-block:: python

   >>> chuck = Person.fetch('cnorris')
   >>> chuck.firstname = 'Carlos'

The careful and the paranoid can see what has changed.  LDAP modifications
only send modification requests for the attributes that have changed.

.. code-block:: python

   >>> chuck.diff()
   {'firstname': ('Chuck', 'Carlos')}

Let's :func:`~ldapper.ldapnode.LDAPNode.save` our changes.

   >>> chuck.save()

:func:`~ldapper.ldapnode.LDAPNode.save` calls the Person's
:func:`~ldapper.ldapnode.LDAPNode.validate` method before doing anything else.
:class:`~ldapper.ldapnode.LDAPNode` has a default implementation that just
returns ``True``.  We can override ``validate()`` and get fancy with what it
means for an object to be valid.

Destroy
-------

All of that brings us to the final operation: destruction.

We can destroy our person by calling :func:`~ldapper.ldapnode.LDAPNode.delete`.

.. code-block:: python

   >>> chuck.delete()
   >>> chuck.exists()
   False
