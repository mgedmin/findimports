#!/usr/bin/python
import os
import sys
import getopt
import logging
import compiler
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


class Module:

    def __init__(self, modname, filename):
        self.modname = modname
        self.filename = filename


class ModuleGraph:

    trackUnusedNames = False

    def __init__(self):
        self.modules = {}
        self.path = sys.path

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
        module.imports = Set([self.findModuleOfName(name, dir)
                              for name in module.imported_names])

    def filenameToModname(self, filename):
        for ext in ('.py', '.so', '.dll'):
            if filename.endswith(ext):
                break
        else:
            raise ValueError('filename has unknown extension', filename)
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

    def findModuleOfName(self, dotted_name, extrapath=None):
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
        logging.warn('could not find out name for %s' % dotted_name)
        return dotted_name

    def isModule(self, dotted_name, extrapath=None):
        if dotted_name in sys.modules:
            return dotted_name
        filename = os.path.sep.join(dotted_name.split('.'))
        path = self.path
        if extrapath:
            path = [extrapath] + path
        for dir in path:
            for ext in ('.py', '.so', '.dll'):
                candidate = os.path.join(dir, filename) + ext
                if os.path.exists(candidate):
                    return self.filenameToModname(candidate)
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


def main():
    import sys
    g = ModuleGraph()
    action = g.printImports
    opts, args = getopt.getopt(sys.argv[1:], 'duni',
                               ['dot', 'unused', 'names', 'imports'])
    for k, v in opts:
        if k in ('-d', '--dot'):
            action = g.printDot
        elif k in ('-u', '--unused'):
            action = g.printUnusedImports
        elif k in ('-n', '--names'):
            action = g.printImportedNames
        elif k in ('-i', '--imports'):
            action = g.printImports
    g.trackUnusedNames = (action == g.printUnusedImports)
    for fn in args:
        g.parseFile(fn)
    action()

if __name__ == '__main__':
    main()

