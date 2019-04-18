from ldapper.connection import BaseConnection
from ldapper.ldapnode import LDAPNode
from ldapper import fields


class Connection(BaseConnection):
    BASE_DN = 'dc=example,dc=com'
    URI = 'ldaps://ldap.example.com'


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
