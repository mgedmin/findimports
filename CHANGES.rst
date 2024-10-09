Changes
=======


2.5.1 (2024-10-09)
------------------

- Add support for Python 3.13.


2.5.0 (2024-05-30)
------------------

- Fixed extension module detection that never worked on Python 3.  See `pull
  request 29 <https://github.com/mgedmin/findimports/pull/29>`_.

- Add ``--attr``/``-A`` to add arbitrary graphviz `graph attributes
  <https://graphviz.org/docs/graph/>`_ to the output.  See `pull
  request 30 <https://github.com/mgedmin/findimports/pull/30>`_.


2.4.0 (2024-02-01)
------------------

- Add support for Python 3.12.

- Change license from GPL to MIT.  See `issue 27
  <https://github.com/mgedmin/findimports/issues/27>`_.

- Add ``--package-externals``/``-pE`` to simplify the module graph.

- Add ``--rmprefix PREFIX``/``-R PREFIX`` to remove a package prefix from
  displayed names.

- Add ``--depth N``/``-D N`` to ignore import statements nested too deep in the
  syntax tree (e.g. in functions or if statements).


2.3.0 (2022-10-27)
------------------

- Rewrote command-line parsing to use argparse.  Options that select an action
  (``--imports``/``--dot``/``--names``/``--unused``) now conflict instead of
  all but the last one being ignored.  See `pull request #20
  <https://github.com/mgedmin/findimports/pull/20>`_.

- Add support for Python 3.11.

- Drop support for Python 3.6.


2.2.0 (2021-12-16)
------------------

- Add support for Python 3.10.

- Add ``--ignore-stdlib`` flag to ignore modules from the Python standard
  library.


2.1.0 (2021-05-16)
------------------

- Add ``--ignore`` flag to ignore files and directories, it can be used multiple
  times. See `pull request #14 <https://github.com/mgedmin/findimports/pull/14>`_.


2.0.0 (2021-05-09)
------------------

- Add support for Python 3.9.

- Drop support for Python 3.5 and 2.7.

- Fix a bug where the encoding of Python files was not determined in the
  same way as by Python itself.  See `issue 15
  <https://github.com/mgedmin/findimports/issues/15>`_.  This requires
  the use of ``tokenize.open`` which is not in Python 2.7.


1.5.2 (2019-10-31)
------------------

- Add support for Python 3.8.

- Fix a bug where a package/module with a name that is a prefix of another
  package/module might accidentally be used instead of the other one (e.g. py
  instead of pylab).  See `issue 10
  <https://github.com/mgedmin/findimports/issues/10>`_.


1.5.1 (2019-04-23)
------------------

- Drop support for Python 3.4.


1.5.0 (2019-03-18)
------------------

- Support Python 3.6 and 3.7.

- Drop support for Python 2.6 and 3.3.

- Suppress duplicate import warnings if the line in question has a comment.


1.4.1 (2016-09-28)
------------------

- Replace ``getopt`` with ``optparse``.  This changes the ``--help``
  message as a side effect (`#4
  <https://github.com/mgedmin/findimports/issues/4>`_).


1.4.0 (2015-06-04)
------------------

- Python 3 support (3.3 and newer).

- Use ``ast`` instead of ``compiler`` (`#1
  <https://github.com/mgedmin/findimports/issues/1>`_).


1.3.2 (2015-04-13)
------------------

- Fix "cannot find datetime" on Ubuntu 14.04 LTS (`#3
  <https://github.com/mgedmin/findimports/issues/3>`_).

- 100% test coverage.


1.3.1 (2014-04-16)
------------------

- Added support for relative imports (e.g. ``from .. import foo``).


1.3.0 (2013-04-10)
------------------

- Moved to Github.

- Drop Python 2.4 and 2.5 support.

- Handle unicode docstrings with doctests.


1.2.14 (2012-02-12)
-------------------

- Recognize builtin modules using ``sys.builtin_module_names``.
  Fixes https://bugs.launchpad.net/findimports/+bug/880989.


1.2.13 (2011-04-18)
-------------------

- Suppress "not a zipfile" warnings about ``*.egg-info`` files listed in
  sys.path.


1.2.12 (2011-04-08)
-------------------

- Handle zipfile errors when there are plain files that are not zip files
  on sys.path.


1.2.11 (2011-03-30)
-------------------

- Fix 'could not find cPickle' errors on Python 2.6 and newer.


1.2.10 (2010-02-05)
-------------------

- Ignore 'from __future__ import ...'.


1.2.9 (2009-07-07)
------------------

- Fixed broken and uninstallable source distribution by adding a MANIFEST.in.


1.2.8 (2009-07-07)
------------------

- Is able to find modules inside zip files (e.g. eggs).

- Fixed deprecation warning on Python 2.6.
