import logging
from functools import partial

import ldap

from ldapper.exceptions import ArgumentError
from ldapper.fields import Field, BinaryField
from ldapper.logging import ProxyLogger
from ldapper.utils import (
    bolded,
    inflect_given_cardinality,
    build_ldap_filter,
    list_items_to_sentence,
    middle_dn,
    print_word_list,
    remove_empty_strings,
    stringify,
)


log = logging.getLogger(__name__)

DEFAULT_OPTIONS = (
    'objectclasses', 'excluded_objectclasses',
    'primary_dnprefix', 'secondary_dnprefix', 'identifying_attrs',
    'searchable_fields', 'human_readable_name', 'dn_format',
)


class Options:

    def __init__(self, meta, cls_name):
        self.meta = meta
        self.objectclasses = []
        self.excluded_objectclasses = []
        self.primary_dnprefix = None
        self.secondary_dnprefix = None
        self.identifying_attrs = []
        self.searchable_fields = []
        self.human_readable_name = cls_name

        if meta:
            for attr_name in DEFAULT_OPTIONS:
                if hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))


class LDAPNodeBase(type):

    def __new__(cls, name, bases, attrs):
        new_cls = super(LDAPNodeBase, cls).__new__(cls, name, bases, attrs)

        attr_meta = attrs.pop('Meta', None)
        meta = attr_meta or getattr(new_cls, 'meta', None)

        new_cls._meta = Options(meta, cls_name=name)

        # Keep track of the fields for convenience
        fields = {}

        parents = [b for b in bases if isinstance(b, LDAPNodeBase)]

        # attrs only contains the attributes defined explicity on this
        # class.  We need to layer in the base classes' attrs.
        for parent in parents:
            fields.update(parent._fields)

        for name, attr in attrs.items():
            if isinstance(attr, Field):
                fields[name] = attr
                if attr.readonly:
                    # this is not the prettiest section of code, but hear me
                    # out: if a Field is readonly, we create it as a property.
                    # This lets us control further modification of the field.

                    # name of the concrete attr that will hold the value
                    ro_name = '__' + name

                    # we create the fget, fset, and fdel functions needed for
                    # a property.  Closures in Python are late-binding, so we
                    # use partial function application to "capture" the
                    # correct value of `name` right here and now.

                    def _fget(name, self):
                        return getattr(self, name)

                    def _fset(name, self, value):
                        self.logger.warning("Cannot modify read-only field '%s'" % name)

                    def _fdel(name, self):
                        self.logger.warning("Cannot delete read-only field '%s'" % name)

                    fget = partial(_fget, ro_name)
                    fset = partial(_fset, name)
                    fdel = partial(_fdel, name)
                    doc = '%s field' % name

                    prop = property(fget, fset, fdel, doc)

                    # set `name` to be our property
                    # set `__name` to be an initial value
                    setattr(new_cls, name, prop)
                    setattr(new_cls, ro_name, attr.default_value())
                else:
                    setattr(new_cls, name, attr.default_value())

        # at this point the parent fields and the immediate fields have both been
        # merged into fields.

        # construct the attrlist. Use to ask ldap for specific attrs to return
        new_cls._attrlist = [f.ldap for f in fields.values()]

        new_cls._system_fields = {n: f for n, f in fields.items() if f.system}
        new_cls._non_system_fields = {n: f for n, f in fields.items() if not f.system}
        new_cls._fields = fields

        # Ensure that there is never more than one primary Field
        #
        # It might be acceptable for a class to have no primary fields
        # yet.  It might be a mixin or an LDAPNode with no fields that is
        # being created to set the connection class, which other classes will
        # inherit from.
        primaries = {k: f for (k, f) in new_cls._fields.items() if f.primary is True}
        if len(primaries) > 1:
            emsg = "%s can only have at most one primary field." % new_cls.__name__
            raise ValueError(emsg)
        if primaries:
            new_cls.primary = list(primaries.keys())[0]
            new_cls._primary_field = list(primaries.values())[0]

        # The class is now ready
        return new_cls


class LDAPNode(object, metaclass=LDAPNodeBase):

    sensitive_attributes = ['userPassword']

    def __init__(self, **kwargs):
        """
        Construct a new LDAPNode.

        Raises:
            TypeError: Raised if unrecognized kwargs are passed in.
        """
        self.logger = ProxyLogger(log)
        self.conn = self.__class__.connection.get_connection()
        self._check_required_fields_present(kwargs.keys())

        for name, value in kwargs.items():
            try:
                field = self._fields[name]
            except KeyError:
                msg = "'%s' is an invalid keyword argument for this function" % name
                raise TypeError(msg)
            # readonly fields are normally not writable.  The init method
            # bypasses this restriction by directly accessing the hidden
            # field that the property is backed by.
            if field.readonly:
                setattr(self, '__' + name, field.coerce_for_python(value))
            else:
                setattr(self, name, field.coerce_for_python(value))

    def __repr__(self):
        return self.dn

    def __hash__(self):
        """
        Return the xor of the attributes that are themselves hashable.

        A meaningful implementation of this method is required to use sets.

        Lists do not define hash values.  We do not attempt to incorporate
        them into the hash value because we would have to sort the lists and
        then assume that the elements of the list are hashable.  This means
        that two objects with different values in their lists could hash to
        the same value.
        """
        hash_result = hash("LTM")
        for attr in self._non_system_fields.keys():
            try:
                hash_result = hash_result ^ hash(getattr(self, attr))
            except TypeError:
                pass
        return hash_result

    def __eq__(self, other):
        if not other:
            return False
        if self.__class__ != other.__class__:
            return False
        for attr in self._non_system_fields.keys():
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __lt__(self, other):
        return getattr(self, self.primary) < getattr(other, other.primary)

    def __str__(self):
        """
        Return a string representation of the LDAPNode.

        This requires the LDAPNode inherited class to have the dn attribute
        and the attrs list set.

        Unprintable attributes *are* printed for __str__, but not for
        pretty_print().
        """
        output = "DN: %s" % self.dn
        # first loop the attrs to figure out what the largest string is
        length = max([len(attr) for attr in self._fields.keys() if getattr(self, attr)])
        # add one more for padding
        length += 1
        output_format = '\n%%%ds: %%s' % length

        for attr in self._fields.keys():
            if isinstance(getattr(self, attr), list):
                for a in getattr(self, attr):
                    if isinstance(a, LDAPNode):
                        output += output_format % (attr, a.dnattr())
                    else:
                        output += output_format % (attr, str(a))
            elif isinstance(getattr(self, attr), LDAPNode):
                output += output_format % (attr, getattr(self, attr).dnattr())
            else:
                if getattr(self, attr) is None:
                    continue
                output += output_format % (attr, str(getattr(self, attr)))
        return output

    def pretty_print(self):
        """
        Return the prettified string version of the object

        Any Fields listed as printable=False will be omitted.
        """
        output = "DN: %s" % self.dn
        length = 0
        bolded_length = 0

        attr_names = list(self._fields.keys())

        # figure out what the longest attribute name is
        # add one more for padding
        length = max(len(attr) for attr in attr_names) + 1
        bolded_length = max(len(bolded(attr)) for attr in attr_names) + 1

        line_length = 79 - length - 1
        output_format = '\n%%%ds: %%s' % bolded_length

        # now that the max line length has been determined, we need to split
        # up the system attributes from all other attributes so that we can
        # print the system attributes last.
        system_attr_names = [n for n, f in self._fields.items() if f.system]
        attr_names = [a for a in attr_names if a not in system_attr_names]

        for attr in attr_names + system_attr_names:
            val = getattr(self, attr)
            if val is None:
                continue

            field = self._fields.get(attr, None)
            if field and not field.printable:
                continue
            if field and isinstance(field, BinaryField):
                o = 'Binary (%d bytes)' % len(val)
                output += output_format % (bolded(attr), o)
            elif isinstance(val, list):
                if len(val) > 0:
                    word_list = print_word_list(val, line_length=line_length)
                    lines = word_list.split("\n")
                    list_output_format = '\n%%%ds:%%s' % bolded_length
                    output += list_output_format % (bolded(attr), lines[0])
                    for line in lines[1:]:
                        tmp_output_format = '\n%s %%s' % (' ' * length)
                        output += tmp_output_format % (line)
            elif isinstance(val, LDAPNode):
                output += output_format % (bolded(attr), val.dnattr())
            else:
                output += output_format % (bolded(attr), val)

        return output

    @property
    def hrn(self):
        """Return human-readable name."""
        return self._meta.human_readable_name

    def _dn(self):
        """
        Return the DN for the current object.

        Dynamically generate the DN for the current object based on the
        current values of the attributes involved in DN construction.
        """
        return '{},{}'.format(self._meta.dn_format % self.dnattrs(), self.conn.basedn)

    @property
    def dn(self):
        return self._dn()

    @dn.setter
    def dn(self, value):
        raise ValueError('DN cannot be set since it is dynamically generated.')

    def dnattr(self):
        """
        Return the RDN attribute value as represented in the Python object,
        not as it necessarily is in the LDAP.
        """
        # TODO this function can have a better name
        return getattr(self, self.primary)

    def dnattrs(self):
        """
        Return a hash mapping attributes to their values for attributes that
        are necessary to uniquely identify the object.  This is useful when
        constructing the DN or when calling a refetch().
        """
        attrs = {}
        for attr in self._meta.identifying_attrs:
            # for lists we will use the first value
            # TODO maybe having ListFields be an identifying_attr should
            # be an error at the time of metaclass creation.
            if isinstance(getattr(self, attr), list):
                attrs[attr] = getattr(self, attr)[0]
            else:
                attrs[attr] = getattr(self, attr)
        return attrs

    @classmethod
    def create(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    @classmethod
    def _fetch_entry(cls, primary=None, dnprefix=None, **kwargs):
        """
        Return a single result entry if unique; else None.

        Sometimes the unmanicured result of this function is all you need if
        you are trying to do a quick existence check through
        LDAPNode.obj_exists().  Otherwise, this function is used by fetch() to
        retrieve a result and parse it out into a proper object.
        """
        if kwargs:
            kwargs = stringify(kwargs)

        if primary is None and cls.primary in kwargs.keys():
            primary = kwargs[cls.primary]
        else:
            # TODO I do not think that you should be able to pass LDAPNodes in
            # if primary is an LDAPNode descendent, then get its dnattr instead
            if isinstance(primary, LDAPNode):
                primary = primary.dnattr()

        if dnprefix is None:
            if kwargs:
                try:
                    dnprefix = cls._meta.primary_dnprefix % kwargs
                except KeyError:
                    # TODO maybe this should throw an exception
                    logging.warning(
                        'Unable to fetch %s %s. Missing keyword' %
                        (cls.hrn, primary)
                        + ' argument for primary dn prefix.')
                    return None
            else:
                dnprefix = cls._meta.secondary_dnprefix
        logging.debug('Fetching %s with dnprefix %s' % (primary, dnprefix))

        conn = getattr(cls, 'connection').get_connection()
        filter = '(&(%s=%s)%s)' % \
            (cls._primary_field.ldap, primary, cls.objectclass_filter())
        basedn = '%s,%s' % (dnprefix, conn.basedn)
        try:
            result = conn.search(basedn=basedn, filter=filter, attrlist=cls._attrlist)
        except ldap.NO_SUCH_OBJECT:
            return None
        except ldap.FILTER_ERROR:
            logging.warning('Unable to fetch %s %s.  Bad LDAP search filter.' %
                            (cls.hrn, primary))
            return None

        # Return a result if and only if there is exactly one result.  If there
        # are multiple results, emit a warning, because the result of a fetch
        # should be unique.
        if result is None:
            return None
        elif len(result) == 1:
            return result.pop()
        elif len(result) == 0:
            return None
        else:
            logging.warning('Found %d results.  Unable to fetch %s %s.' %
                            (len(result), cls.hrn, primary))
            return None

    @classmethod
    def fetch(cls, primary=None, dnprefix=None, **kwargs):
        """
        Searches the LDAP for a particular object and then will attempt to
        load it into the current object.

        Arguments:
            primary -- this is the desired value of the primary identifying
                attribute to be fetched.
            dnprefix -- specify a non-conventional DN prefix.  Otherwise, the
                default one set on the class is used.
            kwargs -- a hash of the collected attributes that will be used
                     to populate the dnprefix
        """
        result = cls._fetch_entry(primary=primary, dnprefix=dnprefix, **kwargs)
        if result is not None:
            dn, entry = result
            obj = cls._parse_ldap_entry(dn, entry)
            logging.debug("Loaded %s %s Successfully" %
                          (obj.__class__.__name__, obj.dnattr()))
            return obj
        else:
            return None

    @classmethod
    def fetch_by(cls, attrs, op='&', **kwargs):
        """
        Searches the LDAP for a particular object and then will attempt to
        load it into the current object.

        Arguments:
            attrs -- a hash of the attributes to search with
            op -- operand '&', '|', '!' for the search
            kwargs -- a hash of the collected attributes that will be used
                to populate the dnprefix
        """
        if not attrs or len(attrs) == 0:
            return None
        filter = '(%s' % op
        for attr in attrs:
            filter += '(%s=%s)' % (attr, attrs[attr])
        filter += ')'
        objects = cls.list(filter=filter, max_results=1, **kwargs)
        try:
            return objects[0]
        except IndexError:
            return None

    @classmethod
    def fetch_by_dn(cls, dn, **kwargs):
        """Fetch an object when the DN is already known"""
        dn_parts = dn.split(',', 1)
        conn = getattr(cls, 'connection').get_connection()
        try:
            rdn_parts = dn_parts[0].split('=', 1)
            if len(rdn_parts) != 2:
                return None
            filter = '(%s=%s)' % tuple(rdn_parts)
        except IndexError:
            return None
        try:
            dnprefix = middle_dn(dn, ',' + conn.basedn)
        except IndexError:
            return None
        objects = cls.list(
            filter=filter, dnprefix=dnprefix, max_results=1, **kwargs)
        try:
            return objects[0]
        except IndexError:
            return None

    def refetch(self):
        """Return a fresh copy of the current object pulled from the LDAP"""
        return self.__class__.fetch(**self.dnattrs())

    def _ldap_entry(self):
        """
        Convert the current object into a dict of attributes

        You can think of this as a serialization method for objects entering
        the LDAP.
        """
        attrs = {}
        objectclasses = self.__class__._meta.objectclasses
        attrs['objectclass'] = [o.encode('utf-8') for o in objectclasses]
        for attr_name, field in self._non_system_fields.items():
            # ignore attributes starting with a "-"
            # also ignore fields that are derived (like DNPartField)
            if attr_name.startswith('-') or field.derived:
                continue

            val = getattr(self, attr_name)
            if val is not None:
                sanitized_val = field.sanitize_for_ldap(val)
                if sanitized_val:
                    attrs[field.ldap] = sanitized_val
        return attrs

    @classmethod
    def _parse_ldap_entry(cls, dn, entry):
        """Turn the raw ldap result into a Python object."""
        kwargs = {}
        for attr_name, field in cls._fields.items():
            kwargs[attr_name] = field.populate(dn, entry)
        return cls(**kwargs)

    def exists(self):
        """Return True if the current object exists in the LDAP"""
        return self.conn.exists(self.dn)

    @classmethod
    def obj_exists(cls, *args, **kwargs):
        """
        Return True if an object exists in the LDAP; False otherwise

        Pass the same arguments you would pass to fetch().
        """
        return cls._fetch_entry(*args, **kwargs) is not None

    @classmethod
    def dn_exists(cls, dn):
        """Return True if the DN exists in the LDAP"""
        return cls.connection.get_connection().exists(dn)

    def validate(self):
        """
        Validate the current LDAPNode

        This function accepts no arguments and returns True, since no
        validation criteria are known at this level.  Subclasses should
        override this method for their specific validation needs.

        Validate is called when trying to save() the current object.
        """
        return True

    def diff(self, with_ldap_names=False, skip_fake_attrs=False):
        """
        Return a hash of values that are different between self and the
        representation of the object in the LDAP.  If the object does not
        exist in the LDAP, every attribute is considered different.

        The returned hash will map a differing attribute name to a tuple
        containing (value_in_ldap, value_in_object), which is essentially
        (old_value, new_value) if self is to be saved.
        """
        results = {}
        refetch = self.refetch()
        for attr_name, field in self._non_system_fields.items():
            # derived fields do not exist as concrete fields on the entry, so
            # they should never show up in the diff.
            if field.derived:
                continue
            if skip_fake_attrs and attr_name.startswith('-'):
                continue

            self_val = getattr(self, attr_name)
            if refetch:
                refetch_val = getattr(refetch, attr_name)
            else:
                refetch_val = None

            # an attribute fetched as [] and set on the object to [''] will not
            # be equal and will be considered different, so sanitize the input
            # to avoid this sort of edge case.
            self_val = remove_empty_strings(self_val)
            refetch_val = remove_empty_strings(refetch_val)

            if self_val != refetch_val:
                if with_ldap_names:
                    results[field.ldap] = (refetch_val, self_val)
                else:
                    results[attr_name] = (refetch_val, self_val)
        return results

    def _save_existing(self):
        """Save an existing object."""
        diff = self.diff(with_ldap_names=False, skip_fake_attrs=True)
        for attr in diff:
            field = self._fields[attr]
            ldap_attr = field.ldap
            old_val, new_val = diff[attr]
            ldap_val = field.sanitize_for_ldap(new_val)
            if ldap_val and new_val is not None:
                # modifying existing attribute
                if old_val:
                    if self.conn.modify_attr(self.dn, ldap_attr, ldap_val):
                        self.log__modify_attr_success(attr, old_val, new_val)
                    else:
                        self.log__modify_attr_failure(attr, new_val)
                # adding previously nonexistant attribute
                else:
                    if self.conn.add_attr(self.dn, ldap_attr, ldap_val):
                        self.log__add_attr_success(attr, new_val)
                    else:
                        self.log__add_attr_failure(attr, new_val)
            # deleting attribute
            else:
                if self.conn.delete_attr(self.dn, ldap_attr):
                    self.log__delete_attr_success(attr)
                else:
                    self.log__delete_attr_failure(attr)

    def _save_new(self):
        """Save a new object."""
        self._before_add_callback()
        if self.conn.add(self.dn, self._ldap_entry()):
            self._after_add_callback()
            self.log__add_success()
        else:
            self.log__add_failure()

    def save(self):
        """
        Save the current LDAPNode to the LDAP

        The object MUST have its validate() method return True at the outset.
        After the object is known to be valid, save() will perform
        modifications on just the attributes that changed if the object already
        exists in the LDAP.  If it's a new object, it does an ADD instead.
        """
        # check that object is valid before saving
        if not self.validate():
            self.log__did_not_validate()
            return False

        if self.exists():
            self._save_existing()
        else:
            self._save_new()

    def delete(self):
        """Deletes the current LDAPNode in the LDAP"""
        self._before_delete_callback()
        if self.dn is not None:
            if self.conn.delete(self.dn):
                self._after_delete_callback()
                self.log__delete_success()
            else:
                self.log__delete_failure()
        else:
            self.log__delete_failure()

    @classmethod
    def list(cls, filter=None, prefix=None, rdn_substring=None,
             search_prefix=None, search_string=None, dnprefix=None,
             max_results=None, **kwargs):
        """
        List all objects in the directory for this class.

        Arguments:
            filter -- the caller can provide a filter to get a subset of the
                list.  This should be an LDAP search filter that INCLUDES the
                surrounding parentheses.
            prefix -- if given, return objects whose RDN starts with the
                string prefix.
            rdn_substring -- if given, return objects whose RDN contains the
                substring.
            search_prefix -- if given, return objects where any of the
                object's class's searchable_fields are matched as a prefix.
            search_string -- if given, return objects where any of the
                object's class's searchable_fields are substring matched.
            dnprefix -- Supply a DN prefix.  If given, kwargs and primary and
                secondary DN prefixes will be ignored.
            max_results -- an integer of how many results to return before
                truncation occurs.  If None, no truncation will occur.
            kwargs -- Options passed in that are used to populate the
                primary_dnprefix.

            The filter, prefix, and kwargs can all be passed and the returned
            results will have all of them satisfied.  Only the use of dnprefix
            and kwargs must be mutually exclusive.
        """
        if kwargs:
            kwargs = stringify(kwargs)

        if dnprefix is None:
            if kwargs:
                try:
                    dnprefix = cls._meta.primary_dnprefix % kwargs
                except KeyError:
                    dnprefix = cls._meta.secondary_dnprefix
            else:
                dnprefix = cls._meta.secondary_dnprefix

        logging.debug('Listing with dnprefix %s' % dnprefix)
        objs = []

        if filter is None:
            filter = cls.objectclass_filter()
        else:
            filter = '(&%s%s)' % (cls.objectclass_filter(), filter)

        if prefix:
            filter = '(&%s(%s=%s*))' % (filter, cls._primary_field.ldap, prefix)

        if rdn_substring:
            filter = '(&%s(%s=*%s*))' % (filter, cls._primary_field.ldap, rdn_substring)

        if search_prefix:
            filter = '(&%s%s)' % (
                filter,
                cls.searchable_fields_search_prefix_filter(
                    search_prefix=search_prefix))

        if search_string:
            filter = '(&%s%s)' % (
                filter,
                cls.searchable_fields_search_string_filter(
                    search_string=search_string))

        conn = cls.connection.get_connection()
        basedn = '{},{}'.format(dnprefix, conn.basedn)
        results = conn.search(basedn=basedn, filter=filter, attrlist=cls._attrlist)
        if max_results:
            num_results_processed = 0
            for dn, entry in results:
                if num_results_processed < max_results:
                    o = cls._parse_ldap_entry(dn, entry)
                    logging.debug("Loaded %s %s Successfully" %
                                  (o.__class__.__name__, o.dnattr()))
                    objs.append(o)
                    num_results_processed += 1
                else:
                    break
        else:
            for dn, entry in results:
                o = cls._parse_ldap_entry(dn, entry)
                logging.debug("Loaded %s %s Successfully" %
                              (o.__class__.__name__, o.dnattr()))
                objs.append(o)
        return objs

    @classmethod
    def _list_by(cls, op, attrs, **kwargs):
        """
        This is a helper method to return objects in the current class that
        have either the union or the intersection of the given dict of
        attributes.

        Attributes:
            op -- either '&', '|', or '!'
            attrs -- a hash mapping attribute names to values to be matched
            kwargs -- any kwargs will be passed straight along to the
                underlying call to cls.list().
        """
        if not attrs or len(attrs) == 0:
            return []
        filter = '(%s' % op
        for attr in attrs:
            filter += '(%s=%s)' % (attr, attrs[attr])
        filter += ')'
        return cls.list(filter=filter, **kwargs)

    @classmethod
    def list_by_union(cls, attrs, **kwargs):
        """
        Return a list of LDAPNodes representing the union of the given
        attribute values

        Attributes:
            attrs -- a hash mapping attribute names to values to be matched
        """
        return cls._list_by(op='|', attrs=attrs, **kwargs)

    @classmethod
    def list_by_negation(cls, attrs, **kwargs):
        """
        Return a list of LDAPNodes represented by the negation of the
        given attritbute and value.  There can only be one attribute
        value pair given, otherwise a exception will be raised.

        Attributes:
            attrs -- a hash mappping of the attribute and value to negate
        """
        if len(attrs) != 1:
            raise ArgumentError('Only one attribute value pair supported')
        return cls._list_by(op='!', attrs=attrs, **kwargs)

    @classmethod
    def list_by(cls, attrs, **kwargs):
        """
        Return a list of LDAPNodes representing the intersection of the
        given attribute values

        Attributes:
            attrs -- a hash mapping attribute names to values to be matched
        """
        return cls._list_by(op='&', attrs=attrs, **kwargs)

    @classmethod
    def _searchable_fields_filter(cls, search_term, template,
                                  searchable_fields=None):
        """
        A helper method for searchable fields

        template must have two value placeholders for the var and the value
        """
        filter = ''

        if searchable_fields is None:
            searchable_fields = cls._meta.searchable_fields
        # TODO searchable_fields, if passed in, will need to be converted from
        # Python names to LDAP names

        for field in searchable_fields:
            filter += template % (field, search_term)

        return '(|%s)' % filter

    @classmethod
    def searchable_fields_search_prefix_filter(cls, search_prefix,
                                               searchable_fields=None):
        """Return a search prefix filter using the searchable_fields"""
        return cls._searchable_fields_filter(
            search_term=search_prefix, template='(%s=%s*)',
            searchable_fields=searchable_fields)

    @classmethod
    def searchable_fields_search_string_filter(cls, search_string,
                                               searchable_fields=None):
        """Return a search substring filter using the searchable_fields"""
        templates = ['(%s=%s)', '(%s=%s*)', '(%s=*%s)', '(%s=*%s*)']
        filter = ''
        for template in templates:
            filter = filter + cls._searchable_fields_filter(
                search_term=search_string, template=template,
                searchable_fields=searchable_fields)
        return '(|%s)' % filter

    def has_attrval(self, var, value):
        """Return True if the var has the value in question; False otherwise"""
        return value in getattr(self, var)

    def _obscure_if_sensitive(self, attr_name, value):
        """
        Return "*****" if the attribute is sensitive.  If the attribute is
        not sensitive, return the actual value.

        The attr_name is the name in LDAP.
        """
        if attr_name in self.__class__.sensitive_attributes:
            return '*****'
        return value

    # Callbacks/Hooks
    # Child classes can override these methods to do something useful
    def _before_add_callback(self):
        """Gets called just before the LDAPNode is added to the LDAP."""
        pass

    def _after_add_callback(self):
        """Gets called just after the LDAPNode is added to the LDAP."""
        pass

    def _before_delete_callback(self):
        """Gets called just before the LDAPNode is deleted from the LDAP."""
        pass

    def _after_delete_callback(self):
        """Gets called just after the LDAPNode is deleted from the LDAP."""
        pass

    # Log messages
    def log__did_not_validate(self):
        """Log a faiure to pass validation"""
        self.logger.error(
            "%s %s did not pass validation." % (self.hrn, self.dnattr()))

    def log__add_success(self):
        """Log a successful add of the current LDAPNode"""
        self.logger.info(
            "%s %s was added." % (self.hrn, self.dnattr()))

    def log__add_failure(self):
        """Log an unsuccessful add of the current LDAPNode"""
        self.logger.error(
            "Could not add %s %s." % (self.hrn, self.dnattr()))

    def log__add_attr_success(self, attr_name, val):
        """Log a successful attribute add on the current LDAPNode"""
        if isinstance(val, list) and len(val) == 1:
            val = list_items_to_sentence(val)
        self.logger.info('Successfully added %s %s to %s %s' %
                         (attr_name,
                          self._obscure_if_sensitive(attr_name, val),
                          self.hrn, self.dnattr()))

    def log__add_attr_failure(self, attr_name, val):
        """Log an unsuccessful attribute add on the current LDAPNode"""
        self.logger.info('Failed to add %s %s to %s %s' %
                         (attr_name,
                          self._obscure_if_sensitive(attr_name, val),
                          self.hrn, self.dnattr()))

    def log__modify_attr_success(self, attr_name, old_val, new_val):
        """Log a successful modification of a field on the current LDAPNode"""
        if isinstance(old_val, list) and isinstance(new_val, list):
            old_val = set(old_val)
            new_val = set(new_val)
            added = list(new_val - old_val)
            removed = list(old_val - new_val)
            if added:
                name = inflect_given_cardinality(attr_name, len(added))
                added = list_items_to_sentence(added)
                self.logger.info(
                    "Added %s %s to %s %s" %
                    (name, added, self.hrn, self.dnattr()))
            if removed:
                name = inflect_given_cardinality(attr_name, len(removed))
                removed = list_items_to_sentence(removed)
                self.logger.info(
                    "Removed %s %s from %s %s" %
                    (name, removed, self.hrn, self.dnattr()))
        else:
            self.logger.info(
                "Changed %s from %s to %s on %s %s" %
                (attr_name,
                 self._obscure_if_sensitive(attr_name, old_val),
                 self._obscure_if_sensitive(attr_name, new_val),
                 self.hrn, self.dnattr()))

    def log__modify_attr_failure(self, attr_name, attr_value):
        """Log a failed modification of a field on the current LDAPNode"""
        if isinstance(attr_value, list):
            attr_value = '"%s"' % (', '.join(attr_value))
        self.logger.error(
            "Failed to set %s to %s on %s %s" %
            (attr_name,
             self._obscure_if_sensitive(attr_name, attr_value),
             attr_value, self.hrn, self.dnattr()))

    def log__delete_success(self):
        """Log a successful removal of an LDAPNode from the LDAP"""
        self.logger.info(
            "%s %s was removed successfully." %
            (self.hrn, self.dnattr()))

    def log__delete_failure(self):
        """Log an unsuccessful removal of an LDAPNode from the LDAP"""
        self.logger.error(
            "%s %s was not removed successfully." %
            (self.hrn, self.dnattr()))

    def log__delete_attr_success(self, attr_name):
        """Log a successful deletion of a field on the current LDAPNode"""
        self.logger.info('Successfully removed %s attribute from %s %s' %
                         (attr_name, self.hrn, self.dnattr()))

    def log__delete_attr_failure(self, attr_name):
        """Log an unsuccessful deletion of a field on the current LDAPNode"""
        self.logger.error('Failed to remove %s attribute from %s %s' %
                          (attr_name, self.hrn, self.dnattr()))

    @classmethod
    def objectclass_filter(cls):
        """Return a string LDAP filter from the objectClass attributes"""
        f = build_ldap_filter(
            op='&', attrname='objectClass', items=cls._meta.objectclasses)
        if cls._meta.excluded_objectclasses:
            n = build_ldap_filter(
                op='!', attrname='objectClass',
                items=cls._meta.excluded_objectclasses)
            f = '(&%s%s)' % (f, n)
        return f

    def attr_difference_since_last_save(self, attr):
        """
        For a given attribute, return a dict of the values added and removed
        between what is in the LDAP and what is in the current object.

        The `attr` in question *must* be a list for calling this method to make
        any sense.
        """
        diff = self.diff()

        if attr not in self._fields.keys():
            raise ArgumentError("%s is not a valid attribute" % attr)

        if attr not in diff:
            return {}

        old_vals, new_vals = diff[attr]
        # we need to check if either old_vals or new_vals is None, since what
        # is passed to set() must be iterable
        if old_vals is None:
            old_vals = []
        if new_vals is None:
            new_vals = []
        old_vals = set(old_vals)
        new_vals = set(new_vals)

        changeset = {}
        changeset['added'] = list(new_vals.difference(old_vals))
        changeset['removed'] = list(old_vals.difference(new_vals))
        return changeset

    def attr_added_since_last_save(self, attr):
        """
        For a given attribute, return a list of the values added between what
        is in the LDAP and what is in the current object.
        """
        return self.attr_difference_since_last_save(attr).get('added', [])

    def attr_removed_since_last_save(self, attr):
        """
        For a given attribute, return a list of the values removed between what
        is in the LDAP and what is in the current object.
        """
        return self.attr_difference_since_last_save(attr).get('removed', [])

    def _check_required_fields_present(self, attrs):
        necessary = set([f for f, val in self._fields.items() if not val.optional])
        available = set(attrs)
        missing = necessary - available
        if missing:
            if len(missing) == 1:
                msg = "Required field '{}' is missing".format(missing.pop())
            else:
                fields = ["'{}'".format(f) for f in missing]
                msg = 'Required fields [{}] are missing'.format(', '.join(fields))
            raise Exception(msg)
