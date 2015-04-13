import unittest

import findimports


class TestModuleGraph(unittest.TestCase):

    def test_isModule(self):
        mg = findimports.ModuleGraph()
        self.assertTrue(mg.isModule('os'))
        self.assertTrue(mg.isModule('sys'))
        self.assertTrue(mg.isModule('datetime'))
        self.assertFalse(mg.isModule('nosuchmodule'))
        self.assertFalse(mg.isModule('logging'))  # it's a package
