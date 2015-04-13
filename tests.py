import unittest
from cStringIO import StringIO

import findimports


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

    def test_isModule(self):
        mg = findimports.ModuleGraph()
        self.assertTrue(mg.isModule('os'))
        self.assertTrue(mg.isModule('sys'))
        self.assertTrue(mg.isModule('datetime'))
        self.assertFalse(mg.isModule('nosuchmodule'))
        self.assertFalse(mg.isModule('logging'))  # it's a package
