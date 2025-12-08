import itertools
import os
import unittest
from io import StringIO

import findimports


here = os.path.dirname(__file__)


class TestModule(unittest.TestCase):

    def test(self):
        m = findimports.Module('foo', 'foo.py')
        self.assertEqual(repr(m), '<Module: foo>')


class TestModuleGraph(unittest.TestCase):

    def setUp(self):
        self.warnings = []

    def warn(self, about, message, *args):
        if args:
            message = message % args
        self.warnings.append(message)

    def test_warn(self):
        mg = findimports.ModuleGraph()
        mg._stderr = StringIO()
        mg.warn('foo', 'no module %s', 'foo')
        self.assertEqual(mg._stderr.getvalue(), 'no module foo\n')

    def test_warn_suppresses_duplicates(self):
        mg = findimports.ModuleGraph()
        mg._stderr = StringIO()
        mg.warn('foo', 'no module foo')
        mg.warn('foo', 'no module foo (again)')
        self.assertEqual(mg._stderr.getvalue(), 'no module foo\n')

    def test_parsePathname_regular_file(self):
        mg = findimports.ModuleGraph()
        mg.warn = self.warn
        mg.parsePathname(__file__.rstrip('co'))  # .pyc -> .py
        self.assertTrue('unittest' in mg.modules[__name__].imports)

    def test_filterIgnores(self):
        dirs = ['venv', 'submodule', '.tox']
        files = ['code.py', 'README.txt', '.#emacsjunk.py']
        mg = findimports.ModuleGraph()
        mg.filterIgnores(dirs, files, ignores=['venv', 'README.txt', '.*'])
        self.assertEqual(dirs, ['submodule'])
        self.assertEqual(files, ['code.py'])

    def test_filenameToModname(self):
        mg = findimports.ModuleGraph()
        if '.x86_64-linux-gnu.so' not in mg._exts:
            mg._exts += ('.x86_64-linux-gnu.so',)
        self.assertEqual(mg.filenameToModname('foo.py'), 'foo')
        self.assertEqual(mg.filenameToModname('foo.so'), 'foo')
        self.assertEqual(mg.filenameToModname('foo.x86_64-linux-gnu.so'),
                         'foo')

    def test_filenameToModname_warns(self):
        mg = findimports.ModuleGraph()
        mg.warn = self.warn
        mg.filenameToModname('foo.xyz')
        self.assertEqual(self.warnings,
                         ['foo.xyz: unknown file name extension'])

    def test_isModule(self):
        mg = findimports.ModuleGraph()
        self.assertTrue(mg.isModule('os'))
        self.assertTrue(mg.isModule('sys'))
        self.assertTrue(mg.isModule('datetime'))
        self.assertFalse(mg.isModule('nosuchmodule'))

    def test_isModule_warns_about_bad_zip_files(self):
        # anything that's a regular file but isn't a valid zip file
        # (oh and it shouldn't end in .egg-info)
        badzipfile = __file__
        mg = findimports.ModuleGraph()
        mg.path = [badzipfile]
        mg.warn = self.warn
        mg.isModule('nosuchmodule')
        self.assertEqual(self.warnings,
                         ['%s: not a directory or zip file' % badzipfile])

    def test_isModule_skips_egginfo_files(self):
        egginfo = os.path.join(here, 'tests', 'sample-tree', 'snake.egg-info')
        mg = findimports.ModuleGraph()
        mg.path = [egginfo]
        mg.warn = self.warn
        mg.isModule('nosuchmodule')
        self.assertEqual(self.warnings, [])

    def test_collapseName(self):
        mg = findimports.ModuleGraph()
        self.assertEqual(mg.collapseName('foo', 2), 'foo')
        self.assertEqual(mg.collapseName('pkg.foo', 2), 'pkg.foo')
        self.assertEqual(mg.collapseName('pkg.subpkg.foo', 2), 'pkg.subpkg')

    def test_packageOf(self):
        mg = findimports.ModuleGraph()
        mg.isPackage = lambda x: x in ['pkg', 'pkg.subpkg']
        self.assertEqual(mg.packageOf('foo'), 'foo')
        self.assertEqual(mg.packageOf('pkg'), 'pkg')
        self.assertEqual(mg.packageOf('pkg.foo'), 'pkg')
        self.assertEqual(mg.packageOf('pkg.subpkg'), 'pkg.subpkg')
        self.assertEqual(mg.packageOf('pkg.subpkg.mod'), 'pkg.subpkg')
        self.assertEqual(mg.packageOf('pkg.subpkg.mod', 1), 'pkg')

    def test_rootOfPackage(self):
        cat_box = os.path.join(here, 'tests', 'sample-tree', 'box', 'cat.py')
        box_root = os.path.join(here, 'tests', 'sample-tree')
        mg = findimports.ModuleGraph()
        self.assertEqual(mg.rootOfPackage(cat_box), box_root)


def make_graph(edges: str) -> findimports.ModuleGraph:
    """Define a module graph using graphviz-like notation."""
    g = findimports.ModuleGraph()
    chains = edges.split(';')
    for chain in chains:
        if not chain.strip():
            continue
        nodes = [s.strip() for s in chain.split('->')]
        for n in nodes:
            if n not in g.modules:
                g.modules[n] = findimports.Module(n, f'{n}.py')
        for u, v in itertools.pairwise(nodes):
            g.modules[u].imports.add(v)
    return g


def test_transitive_closure() -> None:
    mg = make_graph('''
      a -> b -> c;
      b -> d;
      a -> e;
      x -> y;
    ''')
    tr = mg.transitiveClosure()
    assert set(tr) == {'a', 'b', 'c', 'd', 'e', 'x', 'y'}
    assert tr['a'] == {'a', 'b', 'c', 'd', 'e'}
    assert tr['b'] == {'b', 'c', 'd'}
    assert tr['c'] == {'c'}
    assert tr['d'] == {'d'}
    assert tr['x'] == {'x', 'y'}
    assert tr['y'] == {'y'}


def test_transitive_closure_handles_loops() -> None:
    mg = make_graph('''
      a -> b;
      b -> c -> d -> b;
      b -> x;
      c -> y;
      d -> z;
    ''')
    tr = mg.transitiveClosure()
    assert set(tr) == {'a', 'b', 'c', 'd', 'x', 'y', 'z'}
    assert tr['a'] == {'a', 'b', 'c', 'd', 'x', 'y', 'z'}
    assert tr['b'] == {'b', 'c', 'd', 'x', 'y', 'z'}
    assert tr['c'] == {'b', 'c', 'd', 'x', 'y', 'z'}
    assert tr['d'] == {'b', 'c', 'd', 'x', 'y', 'z'}
    assert tr['x'] == {'x'}
    assert tr['y'] == {'y'}
    assert tr['z'] == {'z'}


def test_transitive_reduction() -> None:
    mg = make_graph('''
      a -> b -> c;
      a -> c;
      x -> y;
    ''')
    tr = mg.transitiveReduction()
    assert set(tr.modules) == {'a', 'b', 'c', 'x', 'y'}
    assert tr.modules['a'].imports == {'b'}
    assert tr.modules['b'].imports == {'c'}
    assert tr.modules['c'].imports == set()
    assert tr.modules['x'].imports == {'y'}
    assert tr.modules['y'].imports == set()


def test_transitive_reduction_handles_loops() -> None:
    mg = make_graph('''
      a -> b;
      b -> c -> d -> b;
      c -> x;
      a -> x;
    ''')
    tr = mg.transitiveReduction()
    assert set(tr.modules) == {'a', 'b', 'c', 'd', 'x'}
    assert tr.modules['a'].imports == {'b'}
    assert tr.modules['b'].imports == {'c'}
    assert tr.modules['c'].imports == {'d'}
    assert tr.modules['d'].imports == {'b'}
    assert tr.modules['x'].imports == set()
