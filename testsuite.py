#!/usr/bin/python

import unittest
import doctest
import os
import tempfile
import shutil
import glob
import linecache


def setUp(test):
    test.old_cwd = os.getcwd()
    test.tempdir = tempfile.mkdtemp('findimports')
    os.chdir(test.tempdir)


def tearDown(test):
    os.chdir(test.old_cwd)
    shutil.rmtree(test.tempdir)
    linecache.clearcache()



def additional_tests(): # hook for setuptools
    return unittest.TestSuite(
            doctest.DocFileSuite(filename, setUp=setUp, tearDown=tearDown)
            for filename in sorted(glob.glob('tests/*.txt')))


def main():
    unittest.main(defaultTest='additional_tests')


if __name__ == '__main__':
    main()
