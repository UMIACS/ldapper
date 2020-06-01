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

        # children
        self.AND = []
        self.OR = []

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

        or_filter = ''
        for q in self.OR:
            or_filter += q.compile(cls)
        if len(self.OR) > 1:
            or_filter = f'(|{or_filter})'

        and_filter = ''
        for q in self.AND:
            and_filter += q.compile(cls)
        if len(self.AND) > 1:
            and_filter = f'(&{and_filter})'

        if and_filter and or_filter:
            return f'(&(|{immediate_filter}{or_filter}){and_filter})'
        elif or_filter:
            return f'(|{immediate_filter}{or_filter})'
        elif and_filter:
            return f'(&{immediate_filter}{and_filter})'
        else:
            return immediate_filter

    def __and__(self, other):
        if not isinstance(other, Q):
            raise TypeError(f'not of type Q: {other}')
        self.AND.append(other)
        return self

    def __or__(self, other):
        if not isinstance(other, Q):
            raise TypeError(f'not of type Q: {other}')
        self.OR.append(other)
        return self
