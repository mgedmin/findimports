Changes
=======


1.3.1 (unreleased)
------------------

- Added support for relative imports.


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

