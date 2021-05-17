import os
import unittest

import findimports


try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


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
        dirs = ['venv', 'submodule']
        files = ['code.py', 'README.txt']
        mg = findimports.ModuleGraph()
        mg.filterIgnores(dirs, files, ignores=['venv', 'README.txt'])
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

    def test_packageOf(self):
        mg = findimports.ModuleGraph()
        mg.isPackage = lambda x: x in ['pkg', 'pkg.subpkg']
        self.assertEqual(mg.packageOf('foo'), 'foo')
        self.assertEqual(mg.packageOf('pkg'), 'pkg')
        self.assertEqual(mg.packageOf('pkg.foo'), 'pkg')
        self.assertEqual(mg.packageOf('pkg.subpkg'), 'pkg.subpkg')
        self.assertEqual(mg.packageOf('pkg.subpkg.mod'), 'pkg.subpkg')
        self.assertEqual(mg.packageOf('pkg.subpkg.mod', 1), 'pkg')
