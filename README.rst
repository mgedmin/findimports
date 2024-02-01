FindImports
===========

FindImports extracts Python module dependencies by parsing source files.
It can report names that are imported but not used, and it can generate
module import graphs in ASCII or graphviz formats.

A distinguishing feature of findimports used to be that it could parse doctest
code inside docstrings.

Note that not all cases are handled correctly, especially if you use
'import foo.bar.baz'.

If you need to find unused imports in your codebase, I recommend Pyflakes_
instead -- it's better maintained and more reliable.  For import graphs
consider pydeps_.

.. _Pyflakes: https://pypi.org/project/pyflakes/
.. _pydeps: https://pypi.org/project/pydeps/


Misc
----

Home page: https://github.com/mgedmin/findimports

Licence: MIT (https://mit-license.org/)

|buildstatus|_ |appveyor|_ |coverage|_

.. |buildstatus| image:: https://github.com/mgedmin/findimports/workflows/build/badge.svg?branch=master
.. _buildstatus: https://github.com/mgedmin/findimports/actions

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/mgedmin/findimports?branch=master&svg=true
.. _appveyor: https://ci.appveyor.com/project/mgedmin/findimports

.. |coverage| image:: https://coveralls.io/repos/mgedmin/findimports/badge.svg?branch=master
.. _coverage: https://coveralls.io/r/mgedmin/findimports
