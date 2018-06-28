.. :changelog:

History
-------

0.3.2 (2018-06-27)
~~~~~~~~~~~~~~~~~~

* Added support for ``count()`` and ``get()`` between boundaries.

0.3.1 (2018-03-28)
~~~~~~~~~~~~~~~~~~

* Added support for ``func`` calls in ``ExpressionMatcher``. For example ``func.lower(column)``.

0.3.0 (2018-01-24)
~~~~~~~~~~~~~~~~~~

* Added support for ``.one()`` and ``.first()`` methods when stubbing data.
* Fixed bug which incorrectly unified methods after iterating on mock.

0.2.0 (2018-01-13)
~~~~~~~~~~~~~~~~~~

* Added ability to stub real-data by filtering criteria.
  See `#2 <https://github.com/miki725/alchemy-mock/pull/2>`_.

0.1.1 (2018-01-12)
~~~~~~~~~~~~~~~~~~

* Fixed alembic typo in README. oops.

0.1.0 (2018-01-12)
~~~~~~~~~~~~~~~~~~

* First release on PyPI.
