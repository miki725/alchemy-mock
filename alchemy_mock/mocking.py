# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from functools import partial
from itertools import takewhile

from .comparison import ExpressionMatcher
from .compat import mock
from .utils import copy_and_update, indexof, setattr_tmp


Call = type(mock.call)


def sqlalchemy_call(call):
    """
    Convert ``mock.call()`` into call with all parameters wrapped with ``ExpressionMatcher``

    For example::

        >>> args, kwargs = sqlalchemy_call(mock.call(5, foo='bar'))
        >>> isinstance(args[0], ExpressionMatcher)
        True
        >>> isinstance(kwargs['foo'], ExpressionMatcher)
        True
    """
    args, kwargs = call[-2:]

    args = tuple([ExpressionMatcher(i) for i in args])
    kwargs = {k: ExpressionMatcher(v) for k, v in kwargs.items()}

    return Call((args, kwargs), two=True)


class AlchemyMagicMock(mock.MagicMock):
    """
    MagicMock for SQLAlchemy which can compare alchemys expressions in assertions

    For example::

        >>> from sqlalchemy import or_
        >>> from sqlalchemy.sql.expression import column
        >>> c = column('column')
        >>> s = AlchemyMagicMock()

        >>> _ = s.filter(or_(c == 5, c == 10))

        >>> _ = s.filter.assert_called_once_with(or_(c == 5, c == 10))
        >>> _ = s.filter.assert_any_call(or_(c == 5, c == 10))
        >>> _ = s.filter.assert_has_calls([mock.call(or_(c == 5, c == 10))])

        >>> s.reset_mock()
        >>> _ = s.filter(c == 5)
        >>> _ = s.filter.assert_called_once_with(c == 10)
        Traceback (most recent call last):
        ...
        AssertionError: Expected call: filter(BinaryExpression(sql='"column" = :column_1', params={'column_1': 10}))
        Actual call: filter(BinaryExpression(sql='"column" = :column_1', params={'column_1': 5}))
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('__name__', 'Session')
        super(AlchemyMagicMock, self).__init__(*args, **kwargs)

    def _format_mock_call_signature(self, args, kwargs):
        name = self._mock_name or 'mock'
        args, kwargs = sqlalchemy_call(mock.call(*args, **kwargs))
        return mock._format_call_signature(name, args, kwargs)

    def assert_called_with(self, *args, **kwargs):
        args, kwargs = sqlalchemy_call(mock.call(*args, **kwargs))
        return super(AlchemyMagicMock, self).assert_called_with(*args, **kwargs)

    def assert_any_call(self, *args, **kwargs):
        args, kwargs = sqlalchemy_call(mock.call(*args, **kwargs))
        with setattr_tmp(self, 'call_args_list', [sqlalchemy_call(i) for i in self.call_args_list]):
            return super(AlchemyMagicMock, self).assert_any_call(*args, **kwargs)

    def assert_has_calls(self, calls, any_order=False):
        calls = [sqlalchemy_call(i) for i in calls]
        with setattr_tmp(self, 'mock_calls', type(self.mock_calls)([sqlalchemy_call(i) for i in self.mock_calls])):
            return super(AlchemyMagicMock, self).assert_has_calls(calls, any_order)


class UnifiedAlchemyMagicMock(AlchemyMagicMock):
    """
    MagicMock which unifies common SQLALchemy session functions for easier assertions.

    For example::

        >>> from sqlalchemy.sql.expression import column
        >>> c = column('column')

        >>> s = UnifiedAlchemyMagicMock()
        >>> s.query(None).filter(c == 'one').filter(c == 'two').all()
        []
        >>> s.query(None).filter(c == 'three').filter(c == 'four').all()
        []
        >>> s.filter.call_count
        2
        >>> s.filter.assert_any_call(c == 'one', c == 'two')
        >>> s.filter.assert_any_call(c == 'three', c == 'four')

    Also note that only within same query functions are unified.
    After ``.all()`` is called or query is iterated over, future queries are not unified.
    """
    boundary = [
        'all',
        '__iter__',
    ]
    unify = [
        'query',
        'add_columns',
        'join',
        'filter',
        'filter_by',
        'order_by',
    ]

    def __init__(self, *args, **kwargs):
        data = kwargs.pop('data', [])

        kwargs.update({
            'all': AlchemyMagicMock(return_value=data),
            '__iter__': AlchemyMagicMock(return_value=iter(data)),
        })

        kwargs.update({
            k: AlchemyMagicMock(side_effect=partial(self._unify, _mock_name=k))
            for k in self.unify
        })

        super(UnifiedAlchemyMagicMock, self).__init__(*args, **kwargs)

    def _get_previous_call(self, name, calls):
        # get all previous session calls within same session query
        previous_calls = iter(takewhile(lambda i: i[0] not in self.boundary, reversed(calls)))

        # skip last call
        next(previous_calls)

        return next(iter(filter(lambda i: i[0] == name, previous_calls)), None)

    def _unify(self, *args, **kwargs):
        _mock_name = kwargs.pop('_mock_name')

        previous_method_call = self._get_previous_call(_mock_name, self.method_calls)
        previous_mock_call = self._get_previous_call(_mock_name, self.mock_calls)

        if previous_method_call is None:
            return self

        submock = getattr(self, _mock_name)

        # remove immediate call from both filter mock as well as the parent mock object
        # as it was already registered in self.__call__ before this side-effect is called
        submock.call_count -= 1
        submock.call_args_list.pop()
        submock.mock_calls.pop()
        self.method_calls.pop()
        self.mock_calls.pop()

        # remove previous call since we will be inserting new call instead
        submock.call_args_list.pop()
        submock.mock_calls.pop()
        self.method_calls.pop(indexof(previous_method_call, self.method_calls))
        self.mock_calls.pop(indexof(previous_mock_call, self.mock_calls))

        name, pargs, pkwargs = previous_method_call
        args = pargs + args
        kwargs = copy_and_update(pkwargs, kwargs)

        submock.call_args = Call((args, kwargs), two=True)
        submock.call_args_list.append(Call((args, kwargs), two=True))
        submock.mock_calls.append(Call(('', args, kwargs)))

        self.method_calls.append(Call((name, args, kwargs)))
        self.mock_calls.append(Call((name, args, kwargs)))

        return self
