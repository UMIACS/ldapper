
class Q(object):
    """Query class"""

    def __init__(self, **conditions):
        self.conditions = conditions.items()

        # children
        self.AND = []
        self.OR = []

    def compile(self, cls):
        immediate_filter = ''
        for cond_k, cond_v in self.conditions:
            attrname = cls._fields.get(cond_k).ldap
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
        # check that other is of the right type
        self.AND.append(other)
        return self

    def __or__(self, other):
        # check that other is of the right type
        self.OR.append(other)
        return self
