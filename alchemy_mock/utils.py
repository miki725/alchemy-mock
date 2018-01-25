# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from contextlib import contextmanager

import six


def match_type(s, t):
    """
    Match string type

    For example::

        >>> assert type(match_type(b'hello', six.binary_type)) is six.binary_type
        >>> assert type(match_type(u'hello', six.text_type)) is six.text_type
        >>> assert type(match_type(b'hello', six.text_type)) is six.text_type
        >>> assert type(match_type(u'hello', six.binary_type)) is six.binary_type
    """
    if isinstance(s, t):
        return s
    if t is six.text_type:
        return s.decode('utf-8')
    else:
        return s.encode('utf-8')


def copy_and_update(target, updater):
    """
    Copy dictionary and update it all in one operation

    For example::

        >>> a = {'foo': 'bar'}
        >>> b = copy_and_update(a, {1: 2})
        >>> a is b
        False
        >>> b == {'foo': 'bar', 1: 2}
        True
    """
    result = target.copy()
    result.update(updater)
    return result


def indexof(needle, haystack):
    """
    Find an index of ``needle`` in ``haystack`` by looking for exact same item by pointer ids
    vs usual ``list.index()`` which finds by object comparison.

    For example::

        >>> a = {}
        >>> b = {}
        >>> haystack = [1, a, 2, b]
        >>> indexof(b, haystack)
        3
        >>> indexof(None, haystack)
        Traceback (most recent call last):
        ...
        ValueError: None is not in [1, {}, 2, {}]
    """
    for i, item in enumerate(haystack):
        if needle is item:
            return i
    raise ValueError('{!r} is not in {!r}'.format(needle, haystack))


@contextmanager
def setattr_tmp(obj, name, value):
    """
    Utility for temporarily setting value in an object

    For example::

        >>> class Foo(object):
        ...     foo = 'foo'
        >>> print(Foo.foo)
        foo
        >>> with setattr_tmp(Foo, 'foo', 'bar'):
        ...     print(Foo.foo)
        bar
        >>> print(Foo.foo)
        foo

        >>> Foo.foo = None
        >>> with setattr_tmp(Foo, 'foo', 'bar'):
        ...     print(Foo.foo)
        None
    """
    original = getattr(obj, name)

    if original is None:
        yield
        return

    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, original)


def raiser(exp, *args, **kwargs):
    """
    Utility for raising exceptions

    Useful in one-liners

    For example::

        >>> a = lambda x: not x and raiser(ValueError, 'error message')
        >>> _ = a(True)
        >>> _ = a(False)
        Traceback (most recent call last):
        ...
        ValueError: error message
    """
    raise exp(*args, **kwargs)
