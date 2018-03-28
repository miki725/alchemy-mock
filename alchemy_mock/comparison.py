# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
import collections

import six
from sqlalchemy import func
from sqlalchemy.sql.expression import column, or_

from .compat import mock
from .utils import match_type


ALCHEMY_UNARY_EXPRESSION_TYPE = type(column('').asc())
ALCHEMY_BINARY_EXPRESSION_TYPE = type(column('') == '')
ALCHEMY_BOOLEAN_CLAUSE_LIST = type(or_(column('') == '', column('').is_(None)))
ALCHEMY_FUNC_TYPE = type(func.dummy(column('')))
ALCHEMY_TYPES = (
    ALCHEMY_UNARY_EXPRESSION_TYPE,
    ALCHEMY_BINARY_EXPRESSION_TYPE,
    ALCHEMY_BOOLEAN_CLAUSE_LIST,
    ALCHEMY_FUNC_TYPE,
)


class PrettyExpression(object):
    """
    Wrapper around given expression with pretty representations

    For example::

        >>> c = column('column')
        >>> PrettyExpression(c == 5)
        BinaryExpression(sql='"column" = :column_1', params={'column_1': 5})
        >>> PrettyExpression(10)
        10
        >>> PrettyExpression(PrettyExpression(15))
        15
    """
    __slots__ = [
        'expr',
    ]

    def __init__(self, e):
        if isinstance(e, PrettyExpression):
            e = e.expr
        self.expr = e

    def __repr__(self):
        if not isinstance(self.expr, ALCHEMY_TYPES):
            return repr(self.expr)

        compiled = self.expr.compile()

        return '{}(sql={!r}, params={!r})'.format(
            self.expr.__class__.__name__,
            match_type(six.text_type(compiled).replace('\n', ' '), str),
            {match_type(k, str): v for k, v in compiled.params.items()},
        )


class ExpressionMatcher(PrettyExpression):
    """
    Matcher for comparing SQLAlchemy expressions

    Similar to http://www.voidspace.org.uk/python/mock/examples.html#more-complex-argument-matching

    For example::

        >>> c = column('column')
        >>> e1 = c.in_(['foo', 'bar'])
        >>> e2 = c.in_(['foo', 'bar'])
        >>> e3 = c.in_(['cat', 'dog'])
        >>> e4 = c == 'foo'
        >>> e5 = func.lower(c)

        >>> ExpressionMatcher(e1) == mock.ANY
        True
        >>> ExpressionMatcher(e1) == 5
        False
        >>> ExpressionMatcher(e1) == e2
        True
        >>> ExpressionMatcher(e1) != e2
        False
        >>> ExpressionMatcher(e1) == e3
        False
        >>> ExpressionMatcher(e1) == e4
        False
        >>> ExpressionMatcher(e5) == func.lower(c)
        True
        >>> ExpressionMatcher(e5) == func.upper(c)
        False
        >>> ExpressionMatcher(e1) == ExpressionMatcher(e2)
        True

    It also works with nested structures::

        >>> ExpressionMatcher([c == 'foo']) == [c == 'foo']
        True
        >>> ExpressionMatcher({'foo': c == 'foo', 'bar': 5, 'hello': 'world'}) == {'foo': c == 'foo', 'bar': 5, 'hello': 'world'}
        True
    """

    def __eq__(self, other):
        if isinstance(other, type(self)):
            other = other.expr

        # if the right hand side is mock.ANY,
        # mocks comparison will not be used hence
        # we hard-code comparison here
        if isinstance(self.expr, type(mock.ANY)) or isinstance(other, type(mock.ANY)):
            return True

        # handle string comparison bytes vs unicode in dict keys
        if isinstance(self.expr, six.string_types) and isinstance(other, six.string_types):
            other = match_type(other, type(self.expr))

        # compare sqlalchemy public api attributes
        if type(self.expr) is not type(other):
            return False

        if not isinstance(self.expr, ALCHEMY_TYPES):
            def _(v):
                return type(self)(v)

            if isinstance(self.expr, (list, tuple)):
                return all(_(i) == j for i, j in six.moves.zip_longest(self.expr, other))

            elif isinstance(self.expr, collections.Mapping):
                same_keys = self.expr.keys() == other.keys()
                return same_keys and all(_(self.expr[k]) == other[k] for k in self.expr.keys())

            else:
                return self.expr is other or self.expr == other

        expr_compiled = self.expr.compile()
        other_compiled = other.compile()

        if six.text_type(expr_compiled) != six.text_type(other_compiled):
            return False

        if expr_compiled.params != other_compiled.params:
            return False

        return True

    def __ne__(self, other):
        return not (self == other)
