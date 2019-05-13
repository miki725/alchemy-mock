# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from functools import partial
from itertools import chain, takewhile

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from .comparison import ExpressionMatcher
from .compat import mock
from .utils import (
    build_identity_map,
    copy_and_update,
    indexof,
    raiser,
    setattr_tmp,
)


Call = type(mock.call)


class UnorderedTuple(tuple):
    """
    Same as tuple except in comparison order does not matter

    For example::

        >>> UnorderedTuple((1, 2, 3)) == (3, 2, 1)
        True
    """
    def __eq__(self, other):
        if len(self) != len(other):
            return False

        other = list(other)
        for i in self:
            try:
                other.remove(i)
            except ValueError:
                return False

        return True


class UnorderedCall(Call):
    """
    Same as Call except in comparison order of parameters does not matter

    For example::

        >>> UnorderedCall(((1, 2, 3), {'hello': 'world'})) == Call(((3, 2, 1), {'hello': 'world'}))
        True
    """
    def __eq__(self, other):
        _other = list(other)
        _other[-2] = UnorderedTuple(other[-2])
        other = Call(tuple(_other), **{k.replace('_mock_', ''): v for k, v in vars(other).items()})

        return super(UnorderedCall, self).__eq__(other)


def sqlalchemy_call(call, with_name=False, base_call=Call):
    """
    Convert ``mock.call()`` into call with all parameters wrapped with ``ExpressionMatcher``

    For example::

        >>> args, kwargs = sqlalchemy_call(mock.call(5, foo='bar'))
        >>> isinstance(args[0], ExpressionMatcher)
        True
        >>> isinstance(kwargs['foo'], ExpressionMatcher)
        True
    """
    try:
        args, kwargs = call
    except ValueError:
        name, args, kwargs = call
    else:
        name = ''

    args = tuple([ExpressionMatcher(i) for i in args])
    kwargs = {k: ExpressionMatcher(v) for k, v in kwargs.items()}

    if with_name:
        return base_call((name, args, kwargs))
    else:
        return base_call((args, kwargs), two=True)


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

    In addition, mock data be specified to stub real DB interactions.
    Result-sets are specified per filtering criteria so that unique data
    can be returned depending on query/filter/options criteria.
    Data is given as a list of ``(criteria, result)`` tuples where ``criteria``
    is a list of calls.
    Reason for passing data as a list vs a dict is that calls and SQLAlchemy
    expressions are not hashable hence cannot be dict keys.

    For example::

        >>> from sqlalchemy import Column, Integer, String
        >>> from sqlalchemy.ext.declarative import declarative_base

        >>> Base = declarative_base()

        >>> class SomeClass(Base):
        ...     __tablename__ = 'some_table'
        ...     pk1 = Column(Integer, primary_key=True)
        ...     pk2 = Column(Integer, primary_key=True)
        ...     name =  Column(String(50))
        ...     def __repr__(self):
        ...         return str(self.pk1)

        >>> s = UnifiedAlchemyMagicMock(data=[
        ...     (
        ...         [mock.call.query('foo'),
        ...          mock.call.filter(c == 'one', c == 'two')],
        ...         [SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2)]
        ...     ),
        ...     (
        ...         [mock.call.query('foo'),
        ...          mock.call.filter(c == 'one', c == 'two'),
        ...          mock.call.order_by(c)],
        ...         [SomeClass(pk1=2, pk2=2), SomeClass(pk1=1, pk2=1)]
        ...     ),
        ...     (
        ...         [mock.call.filter(c == 'three')],
        ...         [SomeClass(pk1=3, pk2=3)]
        ...     ),
        ... ])

        # .all()
        >>> s.query('foo').filter(c == 'one').filter(c == 'two').all()
        [1, 2]
        >>> s.query('bar').filter(c == 'one').filter(c == 'two').all()
        []
        >>> s.query('foo').filter(c == 'one').filter(c == 'two').order_by(c).all()
        [2, 1]
        >>> s.query('foo').filter(c == 'one').filter(c == 'three').order_by(c).all()
        []
        >>> s.query('foo').filter(c == 'three').all()
        [3]
        >>> s.query(None).filter(c == 'four').all()
        []

        # .iter()
        >>> list(s.query('foo').filter(c == 'two').filter(c == 'one'))
        [1, 2]

        # .count()
        >>> s.query('foo').filter(c == 'two').filter(c == 'one').count()
        2

        # .first()
        >>> s.query('foo').filter(c == 'one').filter(c == 'two').first()
        1
        >>> s.query('bar').filter(c == 'one').filter(c == 'two').first()

        # .one()
        >>> s.query('foo').filter(c == 'three').one()
        3
        >>> s.query('bar').filter(c == 'one').filter(c == 'two').one()
        Traceback (most recent call last):
        ...
        NoResultFound: No row was found for one()
        >>> s.query('foo').filter(c == 'one').filter(c == 'two').one()
        Traceback (most recent call last):
        ...
        MultipleResultsFound: Multiple rows were found for one()

        # .get()
        >>> s.query('foo').get((1, 1))
        1
        >>> s.query('foo').get((4, 4))
        >>> s.query('foo').filter(c == 'two').filter(c == 'one').get((1, 1))
        1
        >>> s.query('foo').filter(c == 'three').get((1, 1))
        1
        >>> s.query('foo').filter(c == 'three').get((4, 4))

    Also note that only within same query functions are unified.
    After ``.all()`` is called or query is iterated over, future queries are not unified.
    """

    boundary = {
        'all': lambda x: x,
        '__iter__': lambda x: iter(x),
        'count': lambda x: len(x),
        'first': lambda x: next(iter(x), None),
        'one': lambda x: (
            x[0] if len(x) == 1 else
            raiser(MultipleResultsFound, 'Multiple rows were found for one()') if x else
            raiser(NoResultFound, 'No row was found for one()')
        ),
        'get': lambda x, idmap: build_identity_map(x).get(idmap),
    }
    unify = {
        'query': None,
        'add_columns': None,
        'join': None,
        'options': None,
        'group_by': None,
        'filter': UnorderedCall,
        'filter_by': UnorderedCall,
        'order_by': None,
        'limit': None,
    }

    def __init__(self, *args, **kwargs):
        kwargs['_mock_default'] = kwargs.pop('default', [])
        kwargs['_mock_data'] = kwargs.pop('data', None)

        kwargs.update({
            k: AlchemyMagicMock(
                side_effect=partial(
                    self._get_data,
                    _mock_name=k,
                ),
            )
            for k in self.boundary
        })

        kwargs.update({
            k: AlchemyMagicMock(
                return_value=self,
                side_effect=partial(
                    self._unify,
                    _mock_name=k,
                ),
            )
            for k in self.unify
        })

        super(UnifiedAlchemyMagicMock, self).__init__(*args, **kwargs)

    def _get_previous_calls(self, calls):
        return iter(takewhile(lambda i: i[0] not in self.boundary, reversed(calls)))

    def _get_previous_call(self, name, calls):
        # get all previous session calls within same session query
        previous_calls = self._get_previous_calls(calls)

        # skip last call
        next(previous_calls)

        return next(iter(filter(lambda i: i[0] == name, previous_calls)), None)

    def _unify(self, *args, **kwargs):
        _mock_name = kwargs.pop('_mock_name')
        submock = getattr(self, _mock_name)

        previous_method_call = self._get_previous_call(_mock_name, self.method_calls)
        previous_mock_call = self._get_previous_call(_mock_name, self.mock_calls)

        if previous_mock_call is None:
            return submock.return_value

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

        return submock.return_value

    def _get_data(self, *args, **kwargs):
        _mock_name = kwargs.pop('_mock_name')
        _mock_default = self._mock_default
        _mock_data = self._mock_data

        if _mock_data is not None:
            previous_calls = [
                sqlalchemy_call(i, with_name=True, base_call=self.unify.get(i[0]) or Call)
                for i in self._get_previous_calls(self.mock_calls[:-1])
            ]
            sorted_mock_data = sorted(_mock_data, key=lambda x: len(x[0]), reverse=True)

            if _mock_name == 'get':
                query_call = [c for c in previous_calls if c[0] == 'query'][0]
                results = list(chain(*[result for calls, result in sorted_mock_data if query_call in calls]))
                return self.boundary[_mock_name](results, *args, **kwargs)

            else:
                for calls, result in sorted_mock_data:
                    calls = [
                        sqlalchemy_call(i, with_name=True, base_call=self.unify.get(i[0]) or Call)
                        for i in calls
                    ]
                    if all(c in previous_calls for c in calls):
                        return self.boundary[_mock_name](result, *args, **kwargs)

        return self.boundary[_mock_name](_mock_default, *args, **kwargs)
