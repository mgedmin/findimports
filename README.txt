FindImports
===========

FindImports extracts Python module dependencies by parsing source files.
It can report names that are imported but not used, and it can generate
module import graphs in ASCII or graphviz formats.

A distinguishing feature of findimports is that it can parse doctest code
inside docstrings.

Note that not all cases are handled correctly, especially if you use
'import foo.bar.baz'.
