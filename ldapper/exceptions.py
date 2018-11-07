class LdapperError(Exception):

    """Base class for exceptions in this module.

        A msg MUST be provided.
    """

    def __str__(self):
        return '(%s) %s' % (self.__class__.__name__, self.msg)


class AddDNFailed(LdapperError):

    """Exception raised when we failed to add a DN to the LDAP

    Attributes:
       dn -- DN that failed to be added
       msg -- explanation of the error
    """

    def __init__(self, dn):
        self.dn = dn
        self.msg = 'Unable to add the DN %s to LDAP' % dn


class ArgumentError(LdapperError):

    """Exception raised when the arguments to a function are invalid

    Attributes:
        msg -- explanation of the error
    """

    def __init__(self, msg):
        self.msg = msg


class DuplicateValue(LdapperError):

    """Tried to write a duplicate value to the LDAP

    Attributes:
       attr -- Attribute name
       value -- Attribute value
    """

    def __init__(self, attr, value):
        self.attr = attr
        self.original_value = value
        if isinstance(value, list):
            dups = [x for x in value if value.count(x) >= 2]
            self.offending_values = list(set(dups))
        else:
            # I'm not sure when something other than a list could have a
            # duplicate value, but just in case...
            self.offending_values = value
        self.msg = 'Attribute "%s" has duplicate value(s): %s' % (
            attr, self.offending_values)


class NoSuchAttrValue(LdapperError):

    """Exception raised when a DN does not have a given value.

    Attributes:
        dn -- the DN that did not exist
        attribute -- the attribute that is not present
        value -- the value that the attribute was expected to have
        msg -- explanation of the error
    """

    def __init__(self, dn, attribute, value):
        self.dn = dn
        self.attribute = attribute
        self.value = value
        self.msg = 'DN %s does not have %s %s' % (dn, attribute, value)


class NoSuchDN(LdapperError):

    """Exception raised when a DN does not exist.

    Attributes:
        dn -- the DN that did not exist
        msg -- explanation of the error
    """

    def __init__(self, dn):
        self.dn = dn
        self.msg = 'DN %s does not exist.' % dn
