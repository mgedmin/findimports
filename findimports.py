#!/usr/bin/python
"""
FindImports is a script that processes Python module dependencies.  Currently
it can be used for finding unused imports and graphing module dependencies
(with graphviz).  FindImports requires Python 2.3.

Syntax: findimports.py [options] [filename|dirname ...]

Options:
  -h, --help        This help message

  -i, --imports     Print dependency graph (default action).
  -d, --dot         Print dependency graph in dot (graphviz) format.
  -n, --names       Print dependency graph with all imported names.

  -u, --unused      Print unused imports.
  -a, --all         Print unused imports even if there's a comment.

  -N, --noext       Omit external dependencies.

  -p, --packages    Convert the module graph to a package graph.
  -l N, --level N   Collapse subpackages deeper than the Nth level.

  -c, --collapse    Collapse dependency cycles
  -T, --tests       Collapse packages named 'tests' and 'ftests' with parent
                    packages

Elaboration:

    findimports.py -u will not complain about import statements that have
    a comment on the same line, e.g.:

        from somewhereelse import somename # reexport

    findimports.py -u -a will ignore comments and print these statements also.

Shortcomings:

    FindImports does not process doctest sections in docstrings.  This may
    cause some imports to be falsely flagged as unused, and may miss other
    imports.

Copyright (c) 2003--2005 Marius Gedminas <marius@pov.lt>

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

import os
import sys
import sets
import getopt
import doctest
import compiler
import linecache
from compiler import ast
from compiler.visitor import ASTVisitor


class ImportFinder(ASTVisitor):
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

    def __init__(self):
        self.imports = []

    def visitImport(self, node):
        for name, imported_as in node.names:
            self.imports.append(name)

    def visitFrom(self, node):
        for name, imported_as in node.names:
            self.imports.append('%s.%s' % (node.modname, name))

    def visitSomethingWithADocstring(self, node):
        self.processDocstring(node.doc)
        for c in node.getChildNodes():
            self.visit(c)

    visitModule = visitSomethingWithADocstring
    visitClass = visitSomethingWithADocstring
    visitFunction = visitSomethingWithADocstring

    def processDocstring(self, docstring):
        if not docstring:
            return
        dtparser = doctest.DocTestParser()
        for example in dtparser.get_examples(docstring):
            ast = compiler.parse(example.source)
            compiler.walk(ast, self)


class UnusedName(object):
    """Instance of an unused import."""

    def __init__(self, name, lineno):
        self.name = name
        self.lineno = lineno


class ImportFinderAndNameTracker(ImportFinder):
    """ImportFinder that also keeps track on used names."""

    def __init__(self):
        ImportFinder.__init__(self)
        self.unused_names = {}

    def visitImport(self, node):
        ImportFinder.visitImport(self, node)
        for name, imported_as in node.names:
            if not imported_as:
                imported_as = name
            if imported_as != "*":
                self.unused_names[imported_as] = UnusedName(imported_as,
                                                            node.lineno)

    def visitFrom(self, node):
        ImportFinder.visitFrom(self, node)
        for name, imported_as in node.names:
            if not imported_as:
                imported_as = name
            if imported_as != "*":
                self.unused_names[imported_as] = UnusedName(imported_as,
                                                            node.lineno)

    def visitName(self, node):
        if node.name in self.unused_names:
            del self.unused_names[node.name]

    def visitGetattr(self, node):
        full_name = [node.attrname]
        parent = node.expr
        while isinstance(parent, compiler.ast.Getattr):
            full_name.append(parent.attrname)
            parent = parent.expr
        if isinstance(parent, compiler.ast.Name):
            full_name.append(parent.name)
            full_name.reverse()
            name = ""
            for part in full_name:
                if name: name = '%s.%s' % (name, part)
                else: name += part
                if name in self.unused_names:
                    del self.unused_names[name]
        for c in node.getChildNodes():
            self.visit(c)


def find_imports(filename):
    """Find all imported names in a given file."""
    ast = compiler.parseFile(filename)
    visitor = ImportFinder()
    compiler.walk(ast, visitor)
    return visitor.imports

def find_imports_and_track_names(filename):
    """Find all imported names in a given file.

    Returns ``(imports, unused)`` where ``imports`` is a list of
    fully-qualified names that are imported, and ``unused`` is a list of
    UnusedName objects.
    """
    ast = compiler.parseFile(filename)
    visitor = ImportFinderAndNameTracker()
    compiler.walk(ast, visitor)
    return visitor.imports, visitor.unused_names


class Module(object):
    """Node in a module dependency graph.

    Packages may also be represented as Module objects.

    ``imports`` is a set of module names this module depends on.

    ``imported_names`` is a list of all names that were imported from other
    modules.

    ``unused_names`` is a list of names that were imported, but are not used.
    """

    def __init__(self, modname, filename):
        self.modname = modname
        self.label = modname
        self.filename = filename
        self.imports = sets.Set()
        self.imported_names = ()
        self.unused_names = ()


class ModuleCycle(object):
    """Node in a condenced module dependency graph.

    A strongly-connected component of one or more modules/packages.
    """

    def __init__(self, modnames):
        self.modnames = modnames
        self.modname = modnames[0]
        self.label = "\n".join(modnames)
        self.imports = sets.Set()


class ModuleGraph(object):
    """Module graph."""

    trackUnusedNames = False
    all_unused = False
    external_dependencies = True

    def __init__(self):
        self.modules = {}
        self.path = sys.path
        self._module_cache = {}
        self._warned_about = sets.Set()

    def parsePathname(self, pathname):
        """Parse one or more source files.

        ``pathname`` may be a file name or a directory name.
        """
        if os.path.isdir(pathname):
            for root, dirs, files in os.walk(pathname):
                for fn in files:
                    # ignore emacsish junk
                    if fn.endswith('.py') and not fn.startswith('.#'):
                        self.parseFile(os.path.join(root, fn))
        else:
            self.parseFile(pathname)

    def parseFile(self, filename):
        """Parse a single file."""
        modname = self.filenameToModname(filename)
        module = Module(modname, filename)
        self.modules[modname] = module
        if self.trackUnusedNames:
            module.imported_names, module.unused_names = \
                    find_imports_and_track_names(filename)
        else:
            module.imported_names = find_imports(filename)
            module.unused_names = None
        dir = os.path.dirname(filename)
        module.imports = sets.Set([self.findModuleOfName(name, filename, dir)
                                   for name in module.imported_names])

    def filenameToModname(self, filename):
        """Convert a filename to a module name."""
        for ext in ('.py', '.so', '.dll'):
            if filename.endswith(ext):
                break
        else:
            print >> sys.stderr, "%s: unknown file name extension" % filename
        longest_prefix_len = 0
        filename = os.path.abspath(filename)
        for prefix in self.path:
            prefix = os.path.abspath(prefix)
            if (filename.startswith(prefix)
                and len(prefix) > longest_prefix_len):
                longest_prefix_len = len(prefix)
        filename = filename[longest_prefix_len:-len('.py')]
        if filename.startswith(os.path.sep):
            filename = filename[len(os.path.sep):]
        modname = ".".join(filename.split(os.path.sep))
        return modname

    def findModuleOfName(self, dotted_name, filename, extrapath=None):
        """Given a fully qualified name, find what module contains it."""
        if dotted_name.endswith('.*'):
            return dotted_name[:-2]
        name = dotted_name
        while name:
            candidate = self.isModule(name, extrapath)
            if candidate:
                return candidate
            candidate = self.isPackage(name, extrapath)
            if candidate:
                return candidate
            name = name[:name.rfind('.')]
        if dotted_name not in self._warned_about:
            print >> sys.stderr, ("%s: could not find %s"
                                  % (filename, dotted_name))
            self._warned_about.add(dotted_name)
        return dotted_name

    def isModule(self, dotted_name, extrapath=None):
        """Is ``dotted_name`` the name of a module?"""
        try:
            return self._module_cache[(dotted_name, extrapath)]
        except KeyError:
            pass
        if dotted_name in sys.modules:
            return dotted_name
        filename = dotted_name.replace('.', os.path.sep)
        if extrapath:
            for ext in ('.py', '.so', '.dll'):
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
            for ext in ('.py', '.so', '.dll'):
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
        return '.'.join(dotted_name.split('.')[:-1][:packagelevel])

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
                package_name = self.packageOf(name)
                if package_name != package.modname: # no loops
                    package.imports.add(package_name)
        graph = ModuleGraph()
        graph.modules = packages
        return graph

    def collapseTests(self, pkgnames=['tests', 'ftests']):
        """Collapse test packages with parent packages."""
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
            imports[u] = sets.Set()
            for v in self.modules[u].imports:
                if v in self.modules:
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
            revimports[u] = sets.Set()
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
        for u in self.modules:
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
            print "%s:" % module.modname
            print "  %s" % "\n  ".join(module.imported_names)

    def printImports(self):
        """Produce a report of dependencies."""
        for module in self.listModules():
            print "%s:" % module.modname
            if self.external_dependencies:
                imports = list(module.imports)
            else:
                imports = [modname for modname in module.imports
                           if modname in self.modules]
            imports.sort()
            print "  %s" % "\n  ".join(imports)

    def printUnusedImports(self):
        """Produce a report of unused imports."""
        for module in self.listModules():
            names = [(unused.lineno, unused.name)
                     for unused in module.unused_names.itervalues()]
            names.sort()
            for lineno, name in names:
                if not self.all_unused:
                    line = linecache.getline(module.filename, lineno)
                    if '#' in line:
                        continue # assume there's a comment explaining why it
                                 # is not used
                print "%s:%s: %s not used" % (module.filename, lineno, name)

    def printDot(self):
        """Produce a dependency graph in dot format."""
        print "digraph ModuleDependencies {"
        print "  node[shape=box];"
        allNames = sets.Set()
        nameDict = {}
        for n, module in enumerate(self.listModules()):
            module._dot_name = "mod%d" % n
            nameDict[module.modname] = module._dot_name
            print "  %s[label=\"%s\"];" % (module._dot_name,
                                           quote(module.label))
            allNames |= module.imports
        print "  node[style=dotted];"
        if self.external_dependencies:
            myNames = sets.Set(self.modules)
            extNames = list(allNames - myNames)
            extNames.sort()
            for n, name in enumerate(extNames):
                nameDict[name] = id = "extmod%d" % n
                print "  %s[label=\"%s\"];" % (id, name)
        for module in self.modules.values():
            for other in module.imports:
                if other in nameDict:
                    print "  %s -> %s;" % (nameDict[module.modname],
                                        nameDict[other]);
        print "}"


def quote(s):
    """Quote a string for graphviz.

    This function is probably incomplete.
    """
    return s.replace("\\", "\\\\").replace('"', '\\"').replace('\n', '\\n')


def main(argv=sys.argv):
    progname = os.path.basename(argv[0])
    helptext = __doc__.strip().replace('findimports.py', progname)
    g = ModuleGraph()
    action = 'printImports'
    condense_to_packages = False
    collapse_cycles = False
    collapse_tests = False
    packagelevel = None
    noext = False
    try:
        opts, args = getopt.gnu_getopt(argv[1:], 'duniahpl:cNT',
                                   ['dot', 'unused', 'all', 'names', 'imports',
                                    'packages', 'level=', 'help', 'collapse',
                                    'noext', 'tests'])
    except getopt.error, e:
        print >> sys.stderr, "%s: %s" % (progname, e)
        print >> sys.stderr, "Try %s --help." % progname
        return 1
    for k, v in opts:
        if k in ('-d', '--dot'):
            action = 'printDot'
        elif k in ('-u', '--unused'):
            action = 'printUnusedImports'
        elif k in ('-a', '--all'):
            g.all_unused = True
        elif k in ('-n', '--names'):
            action = 'printImportedNames'
        elif k in ('-i', '--imports'):
            action = 'printImports'
        elif k in ('-p', '--packages'):
            condense_to_packages = True
        elif k in ('-l', '--level'):
            packagelevel = int(v)
        elif k in ('-c', '--collapse'):
            collapse_cycles = True
        elif k in ('-N', '--noext'):
            noext = True
        elif k in ('-T', '--tests'):
            collapse_tests = True
        elif k in ('-h', '--help'):
            print helptext
            return 0
    g.trackUnusedNames = (action == 'printUnusedImports')
    if not args:
        args = ['.']
    for fn in args:
        g.parsePathname(fn)
    if condense_to_packages:
        g = g.packageGraph(packagelevel)
    if collapse_tests:
        g = g.collapseTests()
    if collapse_cycles:
        g = g.collapseCycles()
    g.external_dependencies = not noext
    getattr(g, action)()
    return 0

if __name__ == '__main__':
    sys.exit(main())

