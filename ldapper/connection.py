from __future__ import print_function
from __future__ import absolute_import

import re
import logging
from getpass import getpass

from six.moves import input, range

import ldap
import ldap.modlist as modlist

from .exceptions import (
    AddDNFailed,
    NoSuchDN,
    NoSuchAttrValue,
    DuplicateValue,
)

log = logging.getLogger(__name__)


class BaseConnection(object):

    """
    A BaseConnection object can be used to connect to a given LDAP server.

    These settings should be set on subclasses to know the server uri and the
    basedn of the LDAP tree:

      :URI:
        The uri should contain the schema, host, and an optional port
        field.

        e.g. ldaps://ldap.example.com

      :BASEDN:
        The base DN of the LDAP tree.
    """

    __human_readable_name__ = 'LDAP'
    attrlist = [
        '*', 'createTimestamp', 'modifyTimestamp',
        'creatorsName', 'modifiersName',
    ]

    # subclasses must define: BASE_DN, and URI

    def __init__(self, logindn, password, uri=None, certfile=None,
                 basedn=None):
        if basedn:
            self.basedn = basedn
        else:
            self.basedn = self.__class__.BASE_DN

        if uri:
            self.uri = uri
        else:
            self.uri = self.URI

        if certfile:
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, certfile)

        self.ldaps = ldap.initialize(self.uri)
        self.ldaps.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

        if logindn is None and password is None:
            self.ldaps.simple_bind_s()
        else:
            fq_logindn = self._fully_qualify_dn(logindn)
            self.ldaps.simple_bind_s(fq_logindn, password)

        self.dn = self.whoami()
        log.debug('login successful: %s on %s', self.dn, self.uri)

    def _fully_qualify_dn(self, logindn):
        """Return a full-qualified login dn."""
        if not re.search('=', logindn) and not re.search('@', logindn):
            logindn = "uid=%s,ou=people,%s" % (logindn, self.basedn)
        return logindn

    @classmethod
    def connect(cls, logindn=None, password=None, uri=None,
                certfile=None, basedn=None, retries=3):
        """
        Attempt to establish a connection using the supplied parameters.

        Return a connection object.  Return None if unsuccessful.
        """
        name = cls.__human_readable_name__

        # tmpuri is the uri name that we'll print in log messages
        if uri is None:
            tmpuri = cls.URI
        else:
            tmpuri = uri

        for x in range(1, retries + 1):
            if logindn is None:
                logindn = input('Enter a %s loginDN or username: ' % name)
            if password is None:
                password = getpass('Password for %s (%s): ' % (name, logindn))
            try:
                return cls(
                    logindn=logindn,
                    password=password,
                    uri=uri,
                    certfile=certfile,
                    basedn=basedn,
                )
            except ldap.LDAPError:
                log.warning('login attempt %d failed: %s on %s', x, logindn, tmpuri)
                password = None  # prompt again for password on next try

        return None  # all retries failed

    @classmethod
    def prompt(cls, logindn=None, password=None, uri=None,
               certfile=None, basedn=None, retries=3):
        """
        Attempt to establish a connection using the supplied parameters.

        This method will set the connection if successful.

        Return the password used if successful and None if unsuccessful.
        """
        name = cls.__human_readable_name__

        # tmpuri is the uri name that we'll print in log messages
        if uri is None:
            tmpuri = cls.URI
        else:
            tmpuri = uri

        for x in range(retries):
            if logindn is None:
                logindn = input('Enter a %s loginDN or username: ' % name)
            if password is None:
                password = getpass('Password for %s (%s): ' % (name, logindn))
            try:
                conn = cls(
                    logindn=logindn,
                    password=password,
                    uri=uri,
                    certfile=certfile,
                    basedn=basedn,
                )
                log.debug('login successful: %s on %s', logindn, tmpuri)
                cls.set_connection(conn)
                return password
            except ldap.LDAPError:
                log.error('login attempt %d failed: %s on %s', x, logindn, tmpuri)
                password = None  # prompt again for password on next try

        return None  # all retries failed

    @classmethod
    def connect_anon(cls, uri=None):
        """Return an anonymous connection to the LDAP"""
        return cls(logindn=None, password=None, uri=uri)

    @classmethod
    def set_connection(cls, conn):
        cls.conn = conn

    @classmethod
    def get_connection(cls):
        """
        Return the ldap connection that was set

        If the connection object has not been set when this method is
        called, then create and set an anonymous connection object.
        """
        try:
            return cls.conn
        except AttributeError:
            cls.set_connection(cls.connect_anon())
            return cls.conn

    def __str__(self):
        return self.uri + ' as ' + self.whoami()

    def __unicode__(self):
        return self.uri + ' as ' + self.whoami()

    def __del__(self):
        self.ldaps.unbind_s()

    def is_anonymous(self):
        return self.dn is None

    def whoami(self):
        """
        Return the full DN of the entity that is bound to this connection

        Return None if this is an anonymous bind.
        """
        answer = self.ldaps.whoami_s()
        if answer is None or answer == '':
            return None  # anonymous bind

        if re.search('^dn:', answer):
            return answer.replace('dn:', '', 1)
        if re.search('^u:', answer):
            return answer.replace('u:', '', 1)

        return None  # should be virtually unreachable

    def whoami_short(self):
        dn = self.whoami()
        if dn is None:
            return dn
        parts = dn.split(',')
        return parts[0].split('=')[1]

    def exists(self, dn):
        scope = ldap.SCOPE_BASE
        try:
            ldap.dn.explode_dn(dn)
        except ldap.DECODING_ERROR:
            return False
        try:
            self.ldaps.search_s(dn, scope)
            return True
        except ldap.NO_SUCH_OBJECT:
            return False

    def search(self, basedn=None, scope=ldap.SCOPE_SUBTREE,
               filter='(objectClass=*)', attrlist=None):
        """
        Perform an LDAP search operation.

        Optional attributes are a basedn, a scope, and a filter.  Use
        ldap.SCOPE_BASE to search the object represented by the basedn itself.
        The default search scope is ldap.SCOPE_SUBTREE.
        """
        if basedn is None:
            basedn = self.basedn
        if attrlist is None:
            attrlist = self.__class__.attrlist
        log.debug('Searching with filter %s in %s under scope %s' %
                  (filter, basedn, scope))
        try:
            return self.ldaps.search_s(basedn, scope, filter, attrlist=attrlist)
        except ldap.SERVER_DOWN:
            log.error('Could not contact the LDAP service.  Server down.')
            # sometimes connections go stale if the server has restarted.

            # there is nothing we can do for un-anonymous connections.
            if not self.is_anonymous():
                raise

            # if the connection is anonymous, we will retry the search
            # using a fresh connection.
            log.warning('Recreating a new anonymous connection.')

            cls = self.__class__
            new_conn = cls.connect_anon()

            # if this search still fails we won't catch it.  If we get
            # past that point, then set the new anon connection and
            # return the result
            #
            # Nota bene: this code is intentionally not recursive!
            result = new_conn.ldaps.search_s(basedn, scope, filter,
                                             attrlist=attrlist)

            cls.set_connection(new_conn)
            return result

    def add(self, dn, attrs):
        try:
            self.ldaps.add_s(dn, modlist.addModlist(attrs))
            log.debug('add %s' % dn)
            return True
        except ldap.INVALID_DN_SYNTAX:
            raise
        except ldap.NO_SUCH_OBJECT:
            raise AddDNFailed(dn)
        except ldap.LDAPError:
            log.error('add %s failed' % dn, exc_info=False)
            raise

    def delete(self, dn):
        try:
            self.ldaps.delete_s(dn)
            log.debug('delete %s' % dn)
            return True
        except ldap.LDAPError:
            log.error('delete %s failed' % dn, exc_info=False)
            return False

    def modify_attr(self, dn, attribute, value):
        tuple = [(ldap.MOD_REPLACE, attribute, value)]
        try:
            self.ldaps.modify_s(dn, tuple)
            log.debug('mod attr %s on %s' % (attribute, dn))
            return True
        except ldap.NO_SUCH_OBJECT:
            raise NoSuchDN(dn=dn)
        except ldap.TYPE_OR_VALUE_EXISTS:
            raise DuplicateValue(attr=attribute, value=value)
        except ldap.LDAPError:
            log.error('mod attr %s on %s failed' % (attribute, dn),
                      exc_info=False)
            raise
            return False

    def add_attr(self, dn, attribute, value):
        tuple = [(ldap.MOD_ADD, attribute, value)]
        try:
            self.ldaps.modify_s(dn, tuple)
            log.debug('add attr %s on %s' % (attribute, dn))
            return True
        except ldap.NO_SUCH_OBJECT:
            raise NoSuchDN(dn=dn)
        except ldap.TYPE_OR_VALUE_EXISTS:
            raise DuplicateValue(attr=attribute, value=value)
        except ldap.LDAPError:
            log.error('add attr %s on %s failed' % (attribute, dn),
                      exc_info=False)
            raise
            return False

    def delete_attr(self, dn, attribute, value=None):
        tuple = [(ldap.MOD_DELETE, attribute, value)]
        try:
            self.ldaps.modify_s(dn, tuple)
            log.debug('del attr %s and value %s on %s' %
                      (attribute, dn, value))
            return True
        except ldap.NO_SUCH_OBJECT:
            raise NoSuchDN(dn=dn)
        except ldap.NO_SUCH_ATTRIBUTE:
            raise NoSuchAttrValue(dn=dn, attribute=attribute, value=value)
        except ldap.LDAPError:
            log.error('del attr %s and value %s on %s failed' %
                      (attribute, value, dn), exc_info=False)
            raise
            return False

    def ldif(self, filter):
        """Return an LDIF string of all results returned for the given filter"""
        log.debug("Using search filter : %s" % filter)

        results = self.search(filter=filter)
        if len(results) == 1:
            log.info("Found 1 entry")
        else:
            log.info("Found %s entries" % len(results))

        output = ''
        for dn, entry in results:
            output += "-" * 72 + "\n"
            output += "DN: %s\n" % dn
            length = 0
            # first loop the attrs to figure out what the largest string is
            for attr in entry.keys():
                if len(attr) > length:
                    length = len(attr)
            # add one more for padding
            length += 1
            output_format = '%%%ds: %%s\n' % length
            for attr, values in entry.items():
                for val in values:
                    output += output_format % (attr, val)
            output += "\n"
        return output
