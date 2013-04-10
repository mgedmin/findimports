FindImports
===========

FindImports extracts Python module dependencies by parsing source files.
It can report names that are imported but not used, and it can generate
module import graphs in ASCII or graphviz formats.

A distinguishing feature of findimports is that it can parse doctest code
inside docstrings.

Note that not all cases are handled correctly, especially if you use
'import foo.bar.baz'.


Misc
----

Home page: https://github.com/mgedmin/findimports

Old project page: https://launchpad.net/findimports

Licence: GPL v2 or later (http://www.gnu.org/copyleft/gpl.html)

|buildstatus|_ |coverage|_

.. |buildstatus| image:: https://api.travis-ci.org/mgedmin/findimports.png?branch=master
.. _buildstatus: https://travis-ci.org/mgedmin/findimports

.. |coverage| image:: https://coveralls.io/repos/mgedmin/findimports/badge.png?branch=master
.. _coverage: https://coveralls.io/r/mgedmin/findimports
