#!/usr/bin/python

import unittest
import doctest
import os
import sys
import tempfile
import shutil
import glob
import linecache


class RedirectToStdout(object):
    """A file-like object that prints to sys.stdout

    A reason to use sys.stderr = RedirectToStdout() instead of assigning
    sys.stderr = sys.stdout is when sys.stdout is later reassigned to a
    different object (e.g. the StringIO that doctests use) and you want
    sys.stderr to always refer to whatever sys.stdout is printing to.

    Not all file methods are implemented, just the ones that were actually
    needed.
    """

    def write(self, msg):
        sys.stdout.write(msg)


def setUp(test):
    test.old_stderr = sys.stderr
    sys.stderr = RedirectToStdout()
    test.old_cwd = os.getcwd()
    test.tempdir = tempfile.mkdtemp('findimports')
    os.chdir(test.tempdir)


def tearDown(test):
    sys.stderr = test.old_stderr
    os.chdir(test.old_cwd)
    shutil.rmtree(test.tempdir)
    linecache.clearcache()


def additional_tests(): # hook for setuptools
    sample_tree = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                               'tests', 'sample-tree'))
    globs = dict(sample_tree=sample_tree)
    return unittest.TestSuite(
            doctest.DocFileSuite(filename, setUp=setUp, tearDown=tearDown,
                                 module_relative=False, globs=globs)
            for filename in sorted(glob.glob('tests/*.txt')))


def main():
    unittest.main(defaultTest='additional_tests')


if __name__ == '__main__':
    main()
