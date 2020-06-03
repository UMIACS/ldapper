Advanced Topics
===============

Complex Queries
---------------

ldapper has rich support for building arbitrarily complex filter queries.
Similar to how Django does this, there is a :class:`~ldapper.query.Q` class
that is the building block of queries.  Q objects can be strung together to
build any boolean query imaginable.

The simplest query we could build would be a single condition:

.. code-block:: python

   from ldapper.query import Q

   Person.filter(
       Q(employeetype='Director')
   )

This will return all the Person objects where employeetype is equal to
director.  The cool thing here is that when the Q object was compiled down, it
figured out what the ldap field names on Person were to build the filter.

We can see that here:

.. code-block:: python

   >>> Q(employeetype='Director').compile(Person)
   '(employeeType=Director)'

Let's do something more interesting.  Let's return all of the people who
are directors with either the first name "Bob" or "Mary".

We would query for those people like this:

.. code-block:: python

   Person.filter(
      Q(employeetype='Director') & (Q(firstname='Bob') | Q(firstname='Mary'))
   )

.. note::

   Normal `operator precedence <https://docs.python.org/3/reference/expressions.html#operator-precedence>`_ rules in Python apply concerning ``&``, ``|``, and parentheses.

Q objects can also contain multiple conditions.  They will all have to match.

.. code-block:: python

   Person.filter(
      Q(firstname='Bob', lastname='Smith')
   )

And of course if you turn logging up to DEBUG levels, you can inspect the
actual filters that are being generated to return results.
