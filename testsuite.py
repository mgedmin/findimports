#!/usr/bin/python

import doctest
import glob
import linecache
import os
import re
import shutil
import sys
import tempfile
import unittest


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


class Checker(doctest.OutputChecker):
    """Doctest output checker for normalizing Windows pathname differences."""

    def check_output(self, want, got, optionflags):
        want = re.sub("sample-tree/[^:]*",
                      lambda m: m.group(0).replace("/", os.path.sep),
                      want)
        return doctest.OutputChecker.check_output(self, want, got, optionflags)


def setUp(test):
    test.old_path = list(sys.path)
    sample_tree = os.path.abspath(os.path.join('tests', 'sample-tree'))
    sys.path.append(os.path.join(sample_tree, 'zippedmodules.zip'))
    test.old_stderr = sys.stderr
    sys.stderr = RedirectToStdout()
    test.old_cwd = os.getcwd()
    test.tempdir = tempfile.mkdtemp(prefix='test-findimports-')
    os.chdir(test.tempdir)


def tearDown(test):
    sys.path[:] = test.old_path
    sys.stderr = test.old_stderr
    os.chdir(test.old_cwd)
    shutil.rmtree(test.tempdir)
    linecache.clearcache()


def create_tree(files):
    f = None
    for line in files.splitlines():
        if line.startswith('-- ') and line.endswith(' --'):
            filename = line.strip('- ')
            if not os.path.isdir(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            if f is not None:
                f.close()
            f = open(filename, 'w')
        elif f is not None:
            f.write(line + '\n')
    if f is not None:
        f.close()


def additional_tests():  # hook for setuptools setup.py test
    # paths relative to __file__ don't work if you run 'figleaf testsuite.py'
    # so we have to use paths relative to os.getcwd()
    sample_tree = os.path.abspath(os.path.join('tests', 'sample-tree'))
    globs = dict(sample_tree=sample_tree)
    doctests = sorted(glob.glob('tests/*.txt'))
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromName('tests'),
        doctest.DocFileSuite(setUp=setUp, tearDown=tearDown,
                             module_relative=False, globs=globs,
                             checker=Checker(),
                             optionflags=doctest.REPORT_NDIFF,
                             *doctests),
    ])


def main():
    unittest.main(defaultTest='additional_tests')


if __name__ == '__main__':
    main()
