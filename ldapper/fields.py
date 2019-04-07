from __future__ import absolute_import

import six

from ldapper.utils import (
    dn_attribute,
    get_attr,
    get_attrlist,
    to_list,
)


class Field(object):

    """
    A representation of an LDAP attribute.

    A ``Field`` knows how to take a value from LDAP and convert it to a Python
    object.  It know how to go the other way, too: taking a Python value
    and converting it to a representation suitable for LDAP modifications.
    """

    derived = False
    """
    Is the ``Field`` derived/inferred/computed?

    When ``derived=True``, the ``Field``:

      * is derived from something like the DN usually
      * is not a concrete attribute in ldap and thus cannot
        be saved to the LDAP
      * should not appear in diff() results
    """

    def __init__(self, ldap, optional=False, readonly=False, printable=True,
                 primary=False):
        """
        Initialize a Field.

        Arguments:
            ldap - the name of the LDAP attribute
            optional - controls whether the field is mandatory during
                       object creation. Defaults to False.
            readonly - The field cannot be modified after creation.
            printable - True if the field should show up in pretty_print()
            primary - True if this is the field that primarily identifies
                    the object.  Defaults to False.  Can only be one per class.
        """
        self.ldap = ldap
        self.optional = optional
        self.readonly = readonly
        self.printable = printable
        self.primary = primary

    def default_value(self):
        """The value used for the field if none is provided."""
        return None

    def coerce_for_python(self, value):
        """
        Returns a transformed value for the ``value`` provided.

        This will get invoked both when loading a value for this Field out
        of the LDAP or when creating a new object.

        The default implementation returns the value unchanged.
        """
        return value


class IntegerField(Field):

    def populate(self, dn, entry):
        val = get_attr(entry, self.ldap)
        if val:
            return val.decode('utf-8')
        else:
            return val

    def coerce_for_python(self, value):
        if value is None and self.optional:
            return None
        try:
            return int(value)
        except ValueError:
            msg = "%s must be an int: got %s" % (self.ldap, value)
            raise ValueError(msg)
        except TypeError:
            msg = "value for %s cannot be converted to an integer" % self.ldap
            raise ValueError(msg)

    def sanitize_for_ldap(self, val):
        if val is None:
            return None
        else:
            return str(val).encode('utf-8')


class StringField(Field):

    def populate(self, dn, entry):
        val = get_attr(entry, self.ldap)
        if val:
            return val.decode('utf-8')
        else:
            return val

    def coerce_for_python(self, value):
        if type(value) == int:
            return str(value)
        return value

    def sanitize_for_ldap(self, val):
        if val:
            if not isinstance(val, six.string_types):
                val = str(val)
            return val.encode('utf-8')
        else:
            return None


class ListField(Field):

    """Lists can only hold Strings at this time."""

    def default_value(self):
        return []

    def populate(self, dn, entry):
        vals = get_attrlist(entry, self.ldap)
        if vals:
            return [v.decode('utf-8') for v in vals]
        else:
            return vals

    def coerce_for_python(self, value):
        return to_list(value)

    def sanitize_for_ldap(self, val):
        return [v.encode('utf-8') for v in val]


class DNPartField(Field):
    """
    A field that comes from a portion of the object's DN.

    e.g. If we had DN: cn=foo,device=device1,ou=devices

        Then we could specify `device` as the part, and get back `device1`
        as the field.

    There is no ability to make a DNPartField optional, since it is
    a part of the DN.
    """

    derived = True

    def populate(self, dn, entry):
        return dn_attribute(dn, self.ldap)

    def coerce_for_python(self, value):
        primary = getattr(value, 'primary', None)
        if primary:
            return getattr(value, primary)
        else:
            return value

    # this field type should never be saved to LDAP, so there is no
    # sanitize_for_ldap() method defined.
    def sanitize_for_ldap(self, val):
        raise RuntimeError('DNPartField.sanitize_for_ldap() should never get called.')


class BinaryField(Field):

    def populate(self, dn, entry):
        return get_attr(entry, self.ldap)

    def sanitize_for_ldap(self, val):
        return val
