class Q(object):
    """
    Query class used to build arbitrarily complex query filters.

    Q objects are strung together and then compiled once we are told what the
    concrete LDAPNode class is going to be.

    The key to the Q class is that it appends conditions when of the same type
    without creating another level of hierarchy, and it spawns child levels
    only when the operations (And, Or) switches.
    """

    def __init__(self, **conditions):
        self.conditions = conditions.items()

    def compile(self, cls):
        immediate_filter = ''
        for cond_k, cond_v in self.conditions:
            try:
                attrname = cls._fields.get(cond_k).ldap
            except AttributeError:
                raise AttributeError(
                    f'{cond_k} is not a valid field on {cls.__name__}: '
                    f'Expected: {list(cls._fields.keys())}')
            immediate_filter += f'({attrname}={cond_v})'

        if len(self.conditions) > 1:
            immediate_filter = f'(&{immediate_filter})'

        return immediate_filter

    def check_type_compat(self, other):
        if not isinstance(other, Q):
            raise TypeError(f'not of type Q: {other}')

    def __or__(self, other):
        self.check_type_compat(other)
        if isinstance(other, Or):
            other.ops.insert(0, self)
            return other
        else:
            return Or([self, other])

    def __and__(self, other):
        self.check_type_compat(other)
        if isinstance(other, And):
            other.ops.insert(0, self)
            return other
        else:
            return And([self, other])


class And(Q):

    def __init__(self, ops):
        self.ops = ops

    def compile(self, cls):
        f = ''
        for op in self.ops:
            f += op.compile(cls)
        return f'(&{f})'

    def __and__(self, other):
        if type(other) is Q:  # And(...) & Q(...)
            # we repack Q(...) objects into one Q() object for each condition.
            # This is so that:
            #   (Q(lastname='Lennon') & Q(lastname='McCartney')) & \
            #       Q(firstname='Ringo', lastname='Starr')
            # Compiles to: (&(sn=Lennon)(sn=McCartney)(givenName=Ringo)(sn=Starr))
            # And not:     (&(sn=Lennon)(sn=McCartney)(&(givenName=Ringo)(sn=Starr)))
            self.ops.extend([Q(**{k: v}) for k, v in other.conditions])
            return self
        elif type(other) is And:  # And(...) & And(...)
            self.ops.extend(other.ops)
            return self
        else:  # And(...) & Or(...)
            return super().__and__(other)


class Or(Q):

    def __init__(self, ops):
        self.ops = ops

    def compile(self, cls):
        f = ''
        for op in self.ops:
            f += op.compile(cls)
        return f'(|{f})'

    def __or__(self, other):
        if type(other) is Q:
            self.ops.append(other)
            return self
        elif type(other) is Or:
            self.ops.extend(other.ops)
            return self
        else:
            return super().__or__(other)
