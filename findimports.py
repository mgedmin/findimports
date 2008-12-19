#!/usr/bin/python
"""
FindImports is a script that processes Python module dependencies.  Currently
it can be used for finding unused imports and graphing module dependencies
(with graphviz).  FindImports requires Python 2.3.

Syntax: findimports.py [options] [filename|dirname ...]

Options:
  -h, --help        This help message

  -i, --imports     Print dependency graph (default action).
  -d, --dot         Print dependency graph in dot format.
  -n, --names       Print dependency graph with all imported names.

  -u, --unused      Print unused imports.
  -a, --all         Print all unused imports (use together with -u).

Copyright (c) 2003, 2004 Marius Gedminas <marius@pov.lt>

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
import compiler
import linecache
from sets import Set
from compiler import ast
from compiler.visitor import ASTVisitor


class ImportFinder(ASTVisitor):
    """AST visitor that collects all imported names in its imports attribute.

    For example, the following import statements in the AST tree

       import a, b.c, d as e
       from q.w.e import x, y as foo, z
       from woof import *

    will cause imports to contain

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


class UnusedName(object):

    def __init__(self, name, lineno):
        self.name = name
        self.lineno = lineno


class ImportFinderAndNametracker(ImportFinder):
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
    """Find all imported names in a given file."""
    ast = compiler.parseFile(filename)
    visitor = ImportFinderAndNametracker()
    compiler.walk(ast, visitor)
    return visitor.imports, visitor.unused_names


class Module(object):

    def __init__(self, modname, filename):
        self.modname = modname
        self.filename = filename


class ModuleGraph(object):

    trackUnusedNames = False
    all_unused = False

    def __init__(self):
        self.modules = {}
        self.path = sys.path
        self._module_cache = {}
        self._warned_about = sets.Set()

    def parsePathname(self, pathname):
        if os.path.isdir(pathname):
            for root, dirs, files in os.walk(pathname):
                for fn in files:
                    # ignore emacsish junk
                    if fn.endswith('.py') and not fn.startswith('.#'):
                        self.parseFile(os.path.join(root, fn))
        else:
            self.parseFile(pathname)

    def parseFile(self, filename):
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
        module.imports = Set([self.findModuleOfName(name, filename, dir)
                              for name in module.imported_names])

    def filenameToModname(self, filename):
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
        candidate = self.isModule(dotted_name + '.__init__', extrapath)
        if candidate:
            candidate = candidate[:-len(".__init__")]
        return candidate

    def listModules(self):
        modules = list(self.modules.items())
        modules.sort()
        return [module for name, module in modules]

    def printImportedNames(self):
        for module in self.listModules():
            print "%s:" % module.modname
            print "  %s" % "\n  ".join(module.imported_names)

    def printImports(self):
        for module in self.listModules():
            print "%s:" % module.modname
            imports = list(module.imports)
            imports.sort()
            print "  %s" % "\n  ".join(imports)

    def printUnusedImports(self):
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
        print "digraph ModuleDependencies {"
        print "  node[shape=box];"
        allNames = Set()
        nameDict = {}
        for n, module in enumerate(self.listModules()):
            module._dot_name = "mod%d" % n
            nameDict[module.modname] = module._dot_name
            print "  %s[label=\"%s\"];" % (module._dot_name, module.modname)
            for name in module.imports:
                if name not in self.modules:
                    allNames.add(name)
        print "  node[style=dotted];"
        names = list(allNames)
        names.sort()
        for n, name in enumerate(names):
            nameDict[name] = id = "extmod%d" % n
            print "  %s[label=\"%s\"];" % (id, name)
        for module in self.modules.values():
            for other in module.imports:
                print "  %s -> %s;" % (nameDict[module.modname],
                                       nameDict[other]);
        print "}"


def main(argv=sys.argv):
    progname = os.path.basename(argv[0])
    helptext = __doc__.strip().replace('findimports.py', progname)
    g = ModuleGraph()
    action = g.printImports
    try:
        opts, args = getopt.getopt(argv[1:], 'duniah',
                                   ['dot', 'unused', 'all', 'names', 'imports',
                                    'help'])
    except getopt.error, e:
        print >> sys.stderr, "%s: %s" % (progname, e)
        print >> sys.stderr, "Try %s --help." % progname
        return 1
    for k, v in opts:
        if k in ('-d', '--dot'):
            action = g.printDot
        elif k in ('-u', '--unused'):
            action = g.printUnusedImports
        elif k in ('-a', '--all'):
            g.all_unused = True
        elif k in ('-n', '--names'):
            action = g.printImportedNames
        elif k in ('-i', '--imports'):
            action = g.printImports
        elif k in ('-h', '--help'):
            print helptext
            return 0
    g.trackUnusedNames = (action == g.printUnusedImports)
    if not args:
        args = ['.']
    for fn in args:
        g.parsePathname(fn)
    action()
    return 0

if __name__ == '__main__':
    sys.exit(main())

