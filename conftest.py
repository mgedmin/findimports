import linecache
import os
import pathlib
import sys

import pytest


here = pathlib.Path(__file__).resolve().parent
sample_tree = pathlib.Path(here, 'tests/sample-tree')


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


class RewriteBackslashes(object):
    """A file-like object that normalizes path separators.

    pytest doesn't allow custom doctest checkers, so I have to do terrible
    crimes like this class.
    """

    def __init__(self):
        self.real_stdout = sys.stdout

    def write(self, msg):
        self.real_stdout.write(msg.replace(os.path.sep, '/'))


def create_tree(files):
    f = None
    try:
        for line in files.splitlines():
            if line.startswith('-- ') and line.endswith(' --'):
                pathname = pathlib.Path(line.strip('- '))
                pathname.parent.mkdir(parents=True, exist_ok=True)
                if f is not None:
                    f.close()
                f = pathname.open('w')
            elif f is not None:
                print(line, file=f)
    finally:
        if f is not None:
            f.close()


@pytest.fixture(autouse=True)
def doctest_setup(doctest_namespace, tmp_path, monkeypatch):
    doctest_namespace['create_tree'] = create_tree
    doctest_namespace['sample_tree'] = str(sample_tree)
    monkeypatch.syspath_prepend(str(sample_tree.joinpath('zippedmodules.zip')))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'stderr', RedirectToStdout())
    monkeypatch.setattr(sys, 'stdout', RewriteBackslashes())
    yield
    linecache.clearcache()
