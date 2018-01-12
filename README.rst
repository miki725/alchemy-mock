===============
SQLAlchemy Mock
===============

.. image:: https://badge.fury.io/py/alembic-mock.png
    :target: http://badge.fury.io/py/alembic-mock

.. image:: https://travis-ci.org/miki725/alembic-mock.png?branch=master
    :target: https://travis-ci.org/miki725/alembic-mock

.. image:: https://coveralls.io/repos/miki725/alembic-mock/badge.png?branch=master
    :target: https://coveralls.io/r/miki725/alembic-mock?branch=master

SQLAlchemy mock helpers.

* Free software: MIT license
* GitHub: https://github.com/miki725/alembic-mock

Installing
----------

You can install ``alchemy-mock`` using pip::

    $ pip install alchemy-mock

Why?
----

SQLAlchemy is awesome. Unittests are great.
Accessing DB during tests - not so much.
This library provides easy way to mock SQLAlchemy's session
in unittests while preserving ability to do sane asserts.
Normally SQLAlchemy's expressions cannot be easily compared
as comparison on binary expression produces yet another binary expression::

    >>> type((Model.foo == 5) == (Model.bar == 5))
    <class 'sqlalchemy.sql.elements.BinaryExpression'>

But they can be compared with this library::

    >>> ExpressionMatcher(Model.foo == 5) == (Model.bar == 5)
    False

Using
-----

``ExpressionMatcher`` can be directly used::

    >>> from alchemy_mock.comparison import ExpressionMatcher
    >>> ExpressionMatcher(Model.foo == 5) == (Model.foo == 5)
    True

Alternatively ``AlchemyMagicMock`` can be used to mock out SQLAlchemy session::

    >>> from alchemy_mock.mocking import AlchemyMagicMock
    >>> session = AlchemyMagicMock()
    >>> session.query(Model).filter(Model.foo == 5).all()

    >>> session.query.return_value.filter.assert_called_once_with(Model.foo == 5)

In real world though session can be interacted with multiple times to query some data.
In those cases ``UnifiedAlchemyMagicMock`` can be used which combines various calls for easier assertions::

    >>> from alchemy_mock.mocking import UnifiedAlchemyMagicMock
    >>> session = UnifiedAlchemyMagicMock()

    >>> q = session.query(Model).filter(Model.foo == 5)
    >>> if condition:
    ...     q = q.filter(Model.bar > 10)
    >>> data1 = q.all()
    >>> data2 = q.filter(Model.note == 'hello world').all()

    >>> session.filter.assert_has_calls([
    ...     mock.call(Model.foo == 5, Model.bar > 10),
    ...     mock.call(Model.foo == 5, Model.bar > 10, Model.note == 'hello world'),
    ... ])
