#!/usr/bin/python
"""
FindImports is a script that processes Python module dependencies.  Currently
it can be used for finding unused imports and graphing module dependencies
(with graphviz).

Syntax: findimports.py [options] [filename|dirname ...]

Options:
  -h, --help        This help message

  -i, --imports     Print dependency graph (default action).
  -d, --dot         Print dependency graph in dot (graphviz) format.
  -n, --names       Print dependency graph with all imported names.

  -u, --unused      Print unused imports.
  -a, --all         Print unused imports even if there's a comment.
  --duplicate       Print duplicate imports.
  -v                Print more information (currently only affects --duplicate).

  -N, --noext       Omit external dependencies.

  -p, --packages    Convert the module graph to a package graph.
  -l N, --level N   Collapse subpackages deeper than the Nth level.

  -c, --collapse    Collapse dependency cycles.
  -T, --tests       Collapse packages named 'tests' and 'ftests' with parent
                    packages.

FindImports requires Python 2.6 or later.

Notes:

    findimports processes doctest blocks inside docstrings.

    findimports.py -u will not complain about import statements that have
    a comment on the same line, e.g.:

        from somewhereelse import somename # reexport

    findimports.py -u -a will ignore comments and print these statements also.

Caching:

    If you want to produce several different reports from the same dataset,
    you can do it as follows:

        findimports.py --write-cache foo.importcache dirname
        findimports.py foo.importcache -d -T > graph1.dot
        findimports.py foo.importcache -d -N -c -p -l 2 > graph2.dot


Copyright (c) 2003--2015 Marius Gedminas <marius@pov.lt>

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program; if not, write to the Free Software Foundation, Inc., 675 Mass
Ave, Cambridge, MA 02139, USA.
"""

from __future__ import print_function

import ast
import doctest
import linecache
import optparse
import os
import pickle
import re
import sys
import zipfile
from operator import attrgetter


__version__ = '1.5.0'
__author__ = 'Marius Gedminas <marius@gedmin.as>'
__licence__ = 'GPL v2 or later'
__url__ = 'https://github.com/mgedmin/findimports'


def adjust_lineno(filename, lineno, name):
    """Adjust the line number of an import.

    Needed because import statements can span multiple lines, and our lineno
    is always the first line number.
    """
    line = linecache.getline(filename, lineno)
    # Hack warning: might be fooled by comments
    rx = re.compile(r'\b%s\b' % re.escape(name) if name != '*' else '[*]')
    while line and not rx.search(line):
        lineno += 1
        line = linecache.getline(filename, lineno)
    return lineno


class ImportInfo(object):
    """A record of a name and the location of the import statement."""

    def __init__(self, name, filename, lineno, level):
        self.name = name
        self.filename = filename
        self.lineno = lineno
        self.level = level

    def __repr__(self):
        return '%s(%r, %r, %r, %r)' % (self.__class__.__name__, self.name,
                                   self.filename, self.lineno, self.level)


class ImportFinder(ast.NodeVisitor):
    """AST visitor that collects all imported names in its imports attribute.

    For example, the following import statements in the AST tree

       import a, b.c, d as e
       from q.w.e import x, y as foo, z
       from woof import *

    will cause ``imports`` to contain

       a
       b.c
       d
       q.w.e.x
       q.w.e.y
       q.w.e.z
       woof.*

    """

    lineno_offset = 0       # needed when recursively parsing docstrings

    def __init__(self, filename):
        self.imports = []
        self.filename = filename

    def processImport(self, name, imported_as, full_name, level, node):
        lineno = adjust_lineno(self.filename,
                               self.lineno_offset + node.lineno,
                               name)
        info = ImportInfo(full_name, self.filename, lineno, level)
        self.imports.append(info)

    def visit_Import(self, node):
        for alias in node.names:
            self.processImport(alias.name, alias.asname, alias.name, None, node)

    def visit_ImportFrom(self, node):
        if node.module == '__future__':
            return

        for alias in node.names:
            name = alias.name
            imported_as = alias.asname
            fullname = '%s.%s' % (node.module, name) if node.module else name
            self.processImport(name, imported_as, fullname, node.level, node)

    def visitSomethingWithADocstring(self, node):
        # ClassDef and FunctionDef have a 'lineno' attribute, Module doesn't.
        lineno = getattr(node, 'lineno', None)
        self.processDocstring(ast.get_docstring(node, clean=False), lineno)
        self.generic_visit(node)

    visit_Module = visitSomethingWithADocstring
    visit_ClassDef = visitSomethingWithADocstring
    visit_FunctionDef = visitSomethingWithADocstring

    def processDocstring(self, docstring, lineno):
        if not docstring:
            return
        if lineno is None:
            # Module nodes don't have a lineno
            lineno = 0
        dtparser = doctest.DocTestParser()
        try:
            examples = dtparser.get_examples(docstring)
        except Exception:
            print("{filename}:{lineno}: error while parsing doctest".format(
                filename=self.filename, lineno=lineno), file=sys.stderr)
            raise
        for example in examples:
            try:
                source = example.source
                if not isinstance(source, str):
                    source = source.encode('UTF-8')
                node = ast.parse(source, filename='<docstring>')
            except SyntaxError:
                print("{filename}:{lineno}: syntax error in doctest".format(
                    filename=self.filename, lineno=lineno), file=sys.stderr)
            else:
                self.lineno_offset += lineno + example.lineno
                self.visit(node)
                self.lineno_offset -= lineno + example.lineno


class Scope(object):
    """A namespace."""

    def __init__(self, parent=None, name=None):
        self.parent = parent
        self.name = name
        self.imports = {}
        self.unused_names = {}

    def haveImport(self, name):
        if name in self.imports:
            return True
        if self.parent:
            return self.parent.haveImport(name)
        return False

    def whereImported(self, name):
        if name in self.imports:
            return self.imports[name]
        return self.parent.whereImported(name)

    def addImport(self, name, filename, level, lineno):
        self.unused_names[name] = self.imports[name] = ImportInfo(name,
                                                                  filename,
                                                                  lineno,
                                                                  level)

    def useName(self, name):
        if name in self.unused_names:
            del self.unused_names[name]
        if self.parent:
            self.parent.useName(name)


class ImportFinderAndNameTracker(ImportFinder):
    """ImportFinder that also keeps track on used names."""

    warn_about_duplicates = False
    verbose = False

    def __init__(self, filename):
        ImportFinder.__init__(self, filename)
        self.scope = self.top_level = Scope(name=filename)
        self.scope_stack = []
        self.unused_names = []

    def newScope(self, parent, name=None):
        self.scope_stack.append(self.scope)
        self.scope = Scope(parent, name)

    def leaveScope(self):
        self.unused_names += self.scope.unused_names.values()
        self.scope = self.scope_stack.pop()

    def leaveAllScopes(self):
        # newScope()/leaveScope() calls are always balanced so scope_stack
        # should be empty at this point
        assert not self.scope_stack
        self.unused_names += self.scope.unused_names.values()
        self.unused_names.sort(key=attrgetter('lineno'))

    def processDocstring(self, docstring, lineno):
        self.newScope(self.top_level, 'docstring')
        ImportFinder.processDocstring(self, docstring, lineno)
        self.leaveScope()

    def visit_FunctionDef(self, node):
        self.newScope(self.scope, 'function %s' % node.name)
        ImportFinder.visit_FunctionDef(self, node)
        self.leaveScope()

    def processImport(self, name, imported_as, full_name, level, node):
        ImportFinder.processImport(self, name, imported_as, full_name, level, node)
        if not imported_as:
            imported_as = name
        if imported_as != "*":
            lineno = self.lineno_offset + node.lineno
            if (self.warn_about_duplicates and
                    self.scope.haveImport(imported_as)):
                where = self.scope.whereImported(imported_as).lineno
                line = linecache.getline(self.filename, lineno)
                if '#' not in line:
                    print("{filename}:{lineno}: {name} imported again".format(
                        filename=self.filename, lineno=lineno, name=imported_as), file=sys.stderr)
                    if self.verbose:
                        print("{filename}:{lineno}:   (location of previous import)".format(
                            filename=self.filename, lineno=where), file=sys.stderr)
            else:
                self.scope.addImport(imported_as, self.filename, level, lineno)

    def visit_Name(self, node):
        self.scope.useName(node.id)

    def visit_Attribute(self, node):
        full_name = [node.attr]
        parent = node.value
        while isinstance(parent, ast.Attribute):
            full_name.append(parent.attr)
            parent = parent.value
        if isinstance(parent, ast.Name):
            full_name.append(parent.id)
            full_name.reverse()
            name = ""
            for part in full_name:
                if name:
                    name = '%s.%s' % (name, part)
                else:
                    name += part
                self.scope.useName(name)
        self.generic_visit(node)


def find_imports(filename):
    """Find all imported names in a given file.

    Returns a list of ImportInfo objects.
    """
    with open(filename) as f:
        root = ast.parse(f.read(), filename)
    visitor = ImportFinder(filename)
    visitor.visit(root)
    return visitor.imports


def find_imports_and_track_names(filename, warn_about_duplicates=False,
                                 verbose=False):
    """Find all imported names in a given file.

    Returns ``(imports, unused)``.  Both are lists of ImportInfo objects.
    """
    with open(filename) as f:
        root = ast.parse(f.read(), filename)
    visitor = ImportFinderAndNameTracker(filename)
    visitor.warn_about_duplicates = warn_about_duplicates
    visitor.verbose = verbose
    visitor.visit(root)
    visitor.leaveAllScopes()
    return visitor.imports, visitor.unused_names


class Module(object):
    """Node in a module dependency graph.

    Packages may also be represented as Module objects.

    ``imports`` is a set of module names this module depends on.

    ``imported_names`` is a list of all names that were imported from other
    modules (actually, ImportInfo objects).

    ``unused_names`` is a list of names that were imported, but are not used
    (actually, ImportInfo objects).
    """

    def __init__(self, modname, filename):
        self.modname = modname
        self.label = modname
        self.filename = filename
        self.imports = set()
        self.imported_names = ()
        self.unused_names = ()

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.modname)


class ModuleCycle(object):
    """Node in a condenced module dependency graph.

    A strongly-connected component of one or more modules/packages.
    """

    def __init__(self, modnames):
        self.modnames = modnames
        self.modname = modnames[0]
        self.label = "\n".join(modnames)
        self.imports = set()


class ModuleGraph(object):
    """Module graph."""

    trackUnusedNames = False
    all_unused = False
    warn_about_duplicates = False
    verbose = False
    external_dependencies = True

    # some builtin modules do not exist as separate .so files on disk
    builtin_modules = sys.builtin_module_names

    def __init__(self):
        self.modules = {}
        self.path = sys.path
        self._module_cache = {}
        self._warned_about = set()
        self._stderr = sys.stderr
        self._exts = ('.py', '.so', '.dll')
        if hasattr(sys, '_multiarch'): # pragma: nocover
            # Ubuntu 14.04 LTS renames
            # /usr/lib/python2.7/lib-dynload/datetime.so to
            # /usr/lib/python2.7/lib-dynload/datetime.x86_64-linux-gnu.so
            # (https://github.com/mgedmin/findimports/issues/3)
            self._exts += ('.%s.so' % sys._multiarch, )

    def warn(self, about, message, *args):
        if about in self._warned_about:
            return
        if args:
            message = message % args
        print(message, file=self._stderr)
        self._warned_about.add(about)

    def parsePathname(self, pathname):
        """Parse one or more source files.

        ``pathname`` may be a file name or a directory name.
        """
        if os.path.isdir(pathname):
            for root, dirs, files in os.walk(pathname):
                dirs.sort()
                files.sort()
                for fn in files:
                    # ignore emacsish junk
                    if fn.endswith('.py') and not fn.startswith('.#'):
                        self.parseFile(os.path.join(root, fn))
        elif pathname.endswith('.importcache'):
            self.readCache(pathname)
        else:
            self.parseFile(pathname)

    def writeCache(self, filename):
        """Write the graph to a cache file."""
        with open(filename, 'wb') as f:
            pickle.dump(self.modules, f)

    def readCache(self, filename):
        """Load the graph from a cache file."""
        with open(filename, 'rb') as f:
            self.modules = pickle.load(f)

    def parseFile(self, filename):
        """Parse a single file."""
        modname = self.filenameToModname(filename)
        module = Module(modname, filename)
        self.modules[modname] = module
        if self.trackUnusedNames:
            module.imported_names, module.unused_names = \
                find_imports_and_track_names(filename,
                                             self.warn_about_duplicates,
                                             self.verbose)
        else:
            module.imported_names = find_imports(filename)
            module.unused_names = None
        dir = os.path.dirname(filename)
        module.imports = set(
            [self.findModuleOfName(imp.name, imp.level, filename, dir)
             for imp in module.imported_names])

    def filenameToModname(self, filename):
        """Convert a filename to a module name."""
        for ext in reversed(self._exts):
            if filename.endswith(ext):
                filename = filename[:-len(ext)]
                break
        else:
            self.warn(filename, '%s: unknown file name extension', filename)
        filename = os.path.abspath(filename)
        elements = filename.split(os.path.sep)
        modname = []
        while elements:
            modname.append(elements[-1])
            del elements[-1]
            if not os.path.exists(os.path.sep.join(elements + ['__init__.py'])):
                break
        modname.reverse()
        modname = ".".join(modname)
        return modname

    def findModuleOfName(self, dotted_name, level, filename, extrapath=None):
        """Given a fully qualified name, find what module contains it."""
        if dotted_name.endswith('.*'):
            return dotted_name[:-2]
        name = dotted_name

        # extrapath is None only in a couple of test cases; in real life it's
        # always present
        if level and level > 1 and extrapath:
            # strip trailing path bits for each extra level to account for
            # relative imports
            # from . import X has level == 1 and nothing is stripped (the level > 1 check accounts for this case)
            # from .. import X has level == 2 and one trailing path component must go
            # from ... import X has level == 3 and two trailing path components must go
            extrapath = extrapath.split(os.path.sep)
            level -= 1
            extrapath = extrapath[0:-level]
            extrapath = os.path.sep.join(extrapath)

        while name:
            candidate = self.isModule(name, extrapath)
            if candidate:
                return candidate
            candidate = self.isPackage(name, extrapath)
            if candidate:
                return candidate
            name = name[:name.rfind('.')]
        self.warn(dotted_name, '%s: could not find %s', filename, dotted_name)
        return dotted_name

    def isModule(self, dotted_name, extrapath=None):
        """Is ``dotted_name`` the name of a module?"""
        try:
            return self._module_cache[(dotted_name, extrapath)]
        except KeyError:
            pass
        if dotted_name in sys.modules or dotted_name in self.builtin_modules:
            return dotted_name
        filename = dotted_name.replace('.', os.path.sep)
        if extrapath:
            for ext in self._exts:
                candidate = os.path.join(extrapath, filename) + ext
                if os.path.exists(candidate):
                    modname = self.filenameToModname(candidate)
                    self._module_cache[(dotted_name, extrapath)] = modname
                    return modname
        try:
            return self._module_cache[(dotted_name, None)]
        except KeyError:
            pass
        for dir in self.path:
            if os.path.isfile(dir):
                if dir.endswith('.egg-info'):
                    # distribute creates a setuptools-blah-blah.egg-info
                    # that ends up in sys.path
                    continue
                try:
                    zf = zipfile.ZipFile(dir)
                except zipfile.BadZipfile:
                    self.warn(dir, "%s: not a directory or zip file", dir)
                    continue
                names = zf.namelist()
                for ext in self._exts:
                    candidate = filename + ext
                    if candidate in names:
                        modname = filename.replace(os.path.sep, '.')
                        self._module_cache[(dotted_name, extrapath)] = modname
                        self._module_cache[(dotted_name, None)] = modname
                        return modname
            else:
                for ext in self._exts:
                    candidate = os.path.join(dir, filename) + ext
                    if os.path.exists(candidate):
                        modname = self.filenameToModname(candidate)
                        self._module_cache[(dotted_name, extrapath)] = modname
                        self._module_cache[(dotted_name, None)] = modname
                        return modname
        return None

    def isPackage(self, dotted_name, extrapath=None):
        """Is ``dotted_name`` the name of a package?"""
        candidate = self.isModule(dotted_name + '.__init__', extrapath)
        if candidate:
            candidate = candidate[:-len(".__init__")]
        return candidate

    def packageOf(self, dotted_name, packagelevel=None):
        """Determine the package that contains ``dotted_name``."""
        if '.' not in dotted_name:
            return dotted_name
        if not self.isPackage(dotted_name):
            dotted_name = '.'.join(dotted_name.split('.')[:-1])
        if packagelevel:
            dotted_name = '.'.join(dotted_name.split('.')[:packagelevel])
        return dotted_name

    def removeTestPackage(self, dotted_name, pkgnames=['tests', 'ftests']):
        """Remove tests subpackages from dotted_name."""
        result = []
        for name in dotted_name.split('.'):
            if name in pkgnames:
                break
            result.append(name)
        if not result: # empty names are baad
            return dotted_name
        return '.'.join(result)

    def listModules(self):
        """Return an alphabetical list of all modules."""
        modules = list(self.modules.items())
        modules.sort()
        return [module for name, module in modules]

    def packageGraph(self, packagelevel=None):
        """Convert a module graph to a package graph."""
        packages = {}
        for module in self.listModules():
            package_name = self.packageOf(module.modname, packagelevel)
            if package_name not in packages:
                dirname = os.path.dirname(module.filename)
                packages[package_name] = Module(package_name, dirname)
            package = packages[package_name]
            for name in module.imports:
                package_name = self.packageOf(name, packagelevel)
                if package_name != package.modname: # no loops
                    package.imports.add(package_name)
        graph = ModuleGraph()
        graph.modules = packages
        return graph

    def collapseTests(self, pkgnames=['tests', 'ftests']):
        """Collapse test packages with parent packages.

        Works only with package graphs.
        """
        packages = {}
        for module in self.listModules():
            package_name = self.removeTestPackage(module.modname, pkgnames)
            if package_name == module.modname:
                packages[package_name] = Module(package_name, module.filename)
        for module in self.listModules():
            package_name = self.removeTestPackage(module.modname, pkgnames)
            package = packages[package_name]
            for name in module.imports:
                package_name = self.removeTestPackage(name, pkgnames)
                if package_name != package.modname: # no loops
                    package.imports.add(package_name)
        graph = ModuleGraph()
        graph.modules = packages
        return graph

    def collapseCycles(self):
        """Create a graph with cycles collapsed.

        Collapse modules participating in a cycle to a single node.
        """
        # This algorithm determines Strongly Connected Components.  Look it up.
        # It is adapted to suit our data structures.
        # Phase 0: prepare the graph
        imports = {}
        for u in self.modules:
            imports[u] = set()
            for v in self.modules[u].imports:
                if v in self.modules: # skip external dependencies
                    imports[u].add(v)
        # Phase 1: order the vertices
        visited = {}
        for u in self.modules:
            visited[u] = False
        order = []
        def visit1(u):
            visited[u] = True
            for v in imports[u]:
                if not visited[v]:
                    visit1(v)
            order.append(u)
        for u in self.modules:
            if not visited[u]:
                visit1(u)
        order.reverse()
        # Phase 2: compute the inverse graph
        revimports = {}
        for u in self.modules:
            revimports[u] = set()
        for u in self.modules:
            for v in imports[u]:
                revimports[v].add(u)
        # Phase 3: determine the strongly connected components
        components = {}
        component_of = {}
        for u in self.modules:
            visited[u] = False
        def visit2(u):
            visited[u] = True
            component.append(u)
            for v in revimports[u]:
                if not visited[v]:
                    visit2(v)
        for u in order:
            if not visited[u]:
                component = []
                visit2(u)
                component.sort()
                node = ModuleCycle(component)
                components[node.modname] = node
                for modname in component:
                    component_of[modname] = node
        # Phase 4: construct the condensed graph
        for node in components.values():
            for modname in node.modnames:
                for impname in imports[modname]:
                    other = component_of[impname].modname
                    if other != node.modname:
                        node.imports.add(other)
        graph = ModuleGraph()
        graph.modules = components
        return graph

    def printImportedNames(self):
        """Produce a report of imported names."""
        for module in self.listModules():
            print("%s:" % module.modname)
            print("  %s" % "\n  ".join(imp.name for imp in module.imported_names))

    def printImports(self):
        """Produce a report of dependencies."""
        for module in self.listModules():
            print("%s:" % module.label)
            if self.external_dependencies:
                imports = list(module.imports)
            else:
                imports = [modname for modname in module.imports
                           if modname in self.modules]
            imports.sort()
            print("  %s" % "\n  ".join(imports))

    def printUnusedImports(self):
        """Produce a report of unused imports."""
        for module in self.listModules():
            names = [(unused.lineno, unused.name)
                     for unused in module.unused_names]
            names.sort()
            for lineno, name in names:
                if not self.all_unused:
                    line = linecache.getline(module.filename, lineno)
                    if '#' in line:
                        # assume there's a comment explaining why it's not used
                        continue
                print("%s:%s: %s not used" % (module.filename, lineno, name))

    def printDot(self):
        """Produce a dependency graph in dot format."""
        print("digraph ModuleDependencies {")
        print("  node[shape=box];")
        allNames = set()
        nameDict = {}
        for n, module in enumerate(self.listModules()):
            module._dot_name = "mod%d" % n
            nameDict[module.modname] = module._dot_name
            print("  %s[label=\"%s\"];" % (module._dot_name,
                                           quote(module.label)))
            allNames |= module.imports
        print("  node[style=dotted];")
        if self.external_dependencies:
            myNames = set(self.modules)
            extNames = list(allNames - myNames)
            extNames.sort()
            for n, name in enumerate(extNames):
                nameDict[name] = id = "extmod%d" % n
                print("  %s[label=\"%s\"];" % (id, name))
        for modname, module in sorted(self.modules.items()):
            for other in sorted(module.imports):
                if other in nameDict:
                    print("  %s -> %s;" % (nameDict[module.modname],
                                           nameDict[other]))
        print("}")


def quote(s):
    """Quote a string for graphviz.

    This function is probably incomplete.
    """
    return s.replace("\\", "\\\\").replace('"', '\\"').replace('\n', '\\n')


def main(argv=None):
    progname = os.path.basename(argv[0]) if argv else None
    description = __doc__.strip().split('\n\n')[0]
    parser = optparse.OptionParser('%prog [options] [filename|dirname ...]',
                                   prog=progname, description=description)
    parser.add_option('-i', '--imports', action='store_const',
                      dest='action', const='printImports',
                      default='printImports',
                      help='print dependency graph (default action)')
    parser.add_option('-d', '--dot', action='store_const',
                      dest='action', const='printDot',
                      help='print dependency graph in dot (graphviz) format')
    parser.add_option('-n', '--names', action='store_const',
                      dest='action', const='printImportedNames',
                      help='print dependency graph with all imported names')
    parser.add_option('-u', '--unused', action='store_const',
                      dest='action', const='printUnusedImports',
                      help='print unused imports')
    parser.add_option('-a', '--all', action='store_true',
                      dest='all_unused',
                      help="don't ignore unused imports when there's a comment on the same line (only affects -u)")
    parser.add_option('--duplicate', action='store_true',
                      dest='warn_about_duplicates',
                      help='warn about duplicate imports')
    parser.add_option('-v', '--verbose', action='store_true',
                      help='print more information (currently only affects --duplicate)')
    parser.add_option('-N', '--noext', action='store_true',
                      help='omit external dependencies')
    parser.add_option('-p', '--packages', action='store_true',
                      dest='condense_to_packages',
                      help='convert the module graph to a package graph')
    parser.add_option('-l', '--level', type='int',
                      dest='packagelevel',
                      help='collapse subpackages to the topmost Nth levels')
    parser.add_option('-c', '--collapse', action='store_true',
                      dest='collapse_cycles',
                      help='collapse dependency cycles')
    parser.add_option('-T', '--tests', action='store_true',
                      dest='collapse_tests',
                      help="collapse packages named 'tests' and 'ftests' with parent packages")
    parser.add_option('-w', '--write-cache', metavar='FILE',
                      help="write a pickle cache of parsed imports; provide the cache filename as the only non-option argument to load it back")
    try:
        opts, args = parser.parse_args(args=argv[1:] if argv else None)
    except SystemExit as e:
        return e.code
    if not args:
        args = ['.']

    g = ModuleGraph()
    g.all_unused = opts.all_unused
    g.warn_about_duplicates = opts.warn_about_duplicates
    g.verbose = opts.verbose
    g.trackUnusedNames = (opts.action == 'printUnusedImports')
    for fn in args:
        g.parsePathname(fn)
    if opts.write_cache:
        g.writeCache(opts.write_cache)
    if opts.condense_to_packages:
        g = g.packageGraph(opts.packagelevel)
    if opts.collapse_tests:
        g = g.collapseTests()
    if opts.collapse_cycles:
        g = g.collapseCycles()
    g.external_dependencies = not opts.noext
    getattr(g, opts.action)()
    return 0


if __name__ == '__main__':  # pragma: nocover
    sys.exit(main())
