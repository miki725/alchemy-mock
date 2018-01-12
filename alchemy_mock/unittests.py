# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from .comparison import ALCHEMY_TYPES, ExpressionMatcher, PrettyExpression


class AlchemyUnittestMixin(object):
    """
    Unittest class mixin for asserting that different SQLAlchemy
    expressions are the same.

    Uses SQLAlchemyExpressionMatcher to do the comparison.

    For example::

        >>> from sqlalchemy.sql.expression import column
        >>> import unittest
        >>> class FooTest(AlchemyUnittestMixin, unittest.TestCase):
        ...     def test_true(self):
        ...         c = column('column')
        ...         self.assertEqual(c == 5, c == 5)
        ...     def test_false(self):
        ...         c = column('column')
        ...         self.assertEqual(c == 5, c == 10)
        >>> FooTest('test_true').test_true()
        >>> FooTest('test_false').test_false()
        Traceback (most recent call last):
        ...
        AssertionError: BinaryExpression(sql='"column" = :column_1', params={'column_1': 5}) != BinaryExpression(sql='"column" = :column_1', params={'column_1': 10})
    """

    def __init__(self, *args, **kwargs):
        super(AlchemyUnittestMixin, self).__init__(*args, **kwargs)

        # add sqlalchemy expression type which will allow to
        # use self.assertEqual
        for t in ALCHEMY_TYPES:
            self.addTypeEqualityFunc(t, 'assertSQLAlchemyExpressionEqual')

    def assertSQLAlchemyExpressionEqual(self, left, right, msg=None):
        """
        Assert that two given sqlalchemy expressions are equal
        as determined by SQLAlchemyExpressionMatcher
        """
        if ExpressionMatcher(left) != right:
            raise self.failureException(msg or '{!r} != {!r}'.format(
                PrettyExpression(left),
                PrettyExpression(right)
            ))
