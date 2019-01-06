from __future__ import absolute_import

import re

import six
from six.moves import map
from inflection import singularize, pluralize


def bolded(val):
    """return a bolded version of the string passed in"""
    return '%s%s%s' % ('\033[1m', val, '\033[0m')


def dn_attribute(dn, attr):
    """Given a full DN return the value of the attribute given"""
    for rdn in dn.split(','):
        if rdn.startswith('%s=' % attr):
            return rdn.split('=', 1)[1]


def strip_dn_path(dn, left=None, right=None):
    """Strip a given string on the right or left or both
       This is case insenstive"""
    dn_path = dn
    if right is not None:
        rpattern = re.compile(right + '$', re.IGNORECASE)
        dn_path = rpattern.sub('', dn_path)
    if left is not None:
        lpattern = re.compile('^' + left, re.IGNORECASE)
        dn_path = lpattern.sub('', dn_path)
    return dn_path


def middle_dn(dn, right):
    """Strip the first DN component and the right and return what's left."""
    try:
        first, rest = dn.split(',', 1)
    except ValueError:
        return None
    return strip_dn_path(rest, right=right)


def get_attr(entry, attr, index=0):
    """ Returns the first (or specfied) entry for a attribute in the
        entry.  This supports the attribute not existing in the entry
        in which case the result will be None."""
    a = entry.get(attr)
    if a is not None:
        return a[index]
    else:
        return None


def get_attrlist(entry, attr):
    """ Returns the list of the attributes in the entry.  If the attribute
        does not exist in the entry it will return None."""
    a = entry.get(attr)
    if a is not None:
        return a
    else:
        return []


def inflect_given_cardinality(word, num_items):
    """
    Return the singular form of the word if `num_items` is 1.  Otherwise,
    return the plural form of the word.
    """
    if num_items == 1:
        return singularize(word)
    else:
        return pluralize(word)


def ldap_filter_string_from_list(op='&', attrname='objectClass', items=None):
    inside = ''.join(['(%s=%s)' % (attrname, item) for item in items])
    return '(%s%s)' % (op, inside)


def list_items_to_sentence(items):
    """
    Given a list, return a sentence containting the items separated by
    commas and the last element separated by "and" if there are more than
    two items.
    """
    if len(items) == 1:
        return str(items[0])
    elif len(items) == 2:
        return '%s and %s' % (items[0], items[1])
    elif len(items) > 1:
        return '%s, and %s' % (', '.join(map(str, items[:-1])), items[-1])


def print_word_list(words, line_length=79):
    """Given an array, print it in a condensed form separated by spaces"""
    chars_left_in_line = line_length
    returning = ''

    for word in words:
        if not isinstance(word, six.string_types):
            word = str(word)
        if chars_left_in_line < len(word):
            returning += '\n'
            chars_left_in_line = line_length
        returning += ' %s' % (word)
        chars_left_in_line -= (len(word) + 1)

    return returning


def remove_empty_strings(val):
    """
    Remove emptry strings from lists and return None if given an empty
    string.  This method is here so that we can tell if two attribute values
    are superficially different or not.

    For example, [] and [''] should not be considered different.  '' and None
    should also not be considered different.
    """
    if type(val) is list:
        return [x for x in val if x]
    elif isinstance(val, six.string_types):
        if len(val) == 0:
            return None
        else:
            return val
    else:
        return val


def stringify(args):
    """
    Given a hash, turn values that are LDAPNode objects into string
    representations based off the primary attribute.
    """
    returning = {}
    for attr in args:
        primary = getattr(args[attr], 'primary', None)
        if primary:
            returning[attr] = getattr(args[attr], primary)
        else:
            returning[attr] = args[attr]
    return returning


def to_list(possible_lst):
    """
    Coerce argument to a list by all means.

    Lists are returned unchanged, strings return a list with a single element,
    and otherwise an empty list is returned.
    """
    if isinstance(possible_lst, list):
        return possible_lst
    elif isinstance(possible_lst, six.string_types):
        return [possible_lst]
    else:
        return []
