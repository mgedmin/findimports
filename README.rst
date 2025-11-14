FindImports
===========

FindImports extracts Python module dependencies by parsing source files.
It can report names that are imported but not used, and it can generate
module import graphs in ASCII or graphviz or JSON formats.

A distinguishing feature of findimports used to be that it could parse doctest
code inside docstrings.

Note that not all cases are handled correctly, especially if you use
'import foo.bar.baz', or rely on PEP 420 implicit namespace packages.

If you need to find unused imports in your codebase, I recommend flake8_
instead -- it's better maintained and more reliable.  For import graphs
consider pydeps_.

.. _flake8: https://pypi.org/project/flake8/
.. _pydeps: https://pypi.org/project/pydeps/


Installation
------------

Use your favorite Python command-line tool installer such as pipx_ or uv_.
Or run it without installing with ::

    uvx findimports --help

.. _pipx: https://pypi.org/project/pipx/
.. _uv: https://pypi.org/project/uv/


Module dependency graphs
------------------------

On larger projects the module graphs tend to be an unreadable mess.  You can
make them clearer by post-processing the graph with ``tred`` to remove graph
edges representing direct dependencies to modules that you're already
transitively depending on::

    uvx findimports -N -q src -d | tred | xdot -

``tred`` is part of graphviz_.  xdot_ is a nice interactive graphviz viewer.

.. _graphviz: https://graphviz.org/
.. _xdot: https://pypi.org/project/xdot/


Misc
----

Home page: https://github.com/mgedmin/findimports

Licence: MIT (https://mit-license.org/)

|buildstatus|_ |coverage|_

.. |buildstatus| image:: https://github.com/mgedmin/findimports/actions/workflows/build.yml/badge.svg?branch=master
.. _buildstatus: https://github.com/mgedmin/findimports/actions

.. |coverage| image:: https://coveralls.io/repos/mgedmin/findimports/badge.svg?branch=master
.. _coverage: https://coveralls.io/r/mgedmin/findimports
