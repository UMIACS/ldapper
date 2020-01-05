.. _hooks:

Hooks/Callbacks
===================

There are four callbacks that can be overridden to perform an action before
or after and object is added or deleted.

.. code-block:: python

   class Person(LDAPNode):
      ...

      def _before_add_callback(self):
         self.logger.info('Being called before add.')

      def _after_add_callback(self):
         self.logger.info('Being called after add.')

      def _before_delete_callback(self):
         self.logger.info('Being called before delete.')

      def _after_delete_callback(self):
         self.logger.info('Being called after delete.')

_before_add_callback
----------
Gets called just before the LDAPNode is added to the LDAP.

_after_add_callback
----------
Gets called just after the LDAPNode is added to the LDAP.

.. note::
   :func:`~ldapper.ldapnode.LDAPNode._before_add_callback` and
   :func:`~ldapper.ldapnode.LDAPNode._after_add_callback`
   are only called when saving a new object, not when saving existing objects.

_before_delete_callback
----------
Gets called just before the LDAPNode is deleted from the LDAP.

_after_delete_callback
----------
Gets called just after the LDAPNode is deleted from the LDAP.
