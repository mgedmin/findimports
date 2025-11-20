import doctest
import linecache
import os
import pathlib
import re
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


class Checker(doctest.OutputChecker):
    """Doctest output checker for normalizing Windows pathname differences."""

    def check_output(self, want, got, optionflags):
        want = re.sub(
            "sample-tree/[^:]*",
            lambda m: m.group(0).replace("/", os.path.sep),
            want,
        )
        return super().check_output(want, got, optionflags)


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


@pytest.fixture(autouse=True, scope='session')
def doctest_session_setup(request):
    checker = Checker()
    session = request.node
    for item in session.items:
        if isinstance(item, pytest.DoctestItem):
            # This is fragile, but currently there's no better way:
            # https://github.com/pytest-dev/pytest/issues/13003
            item.runner._checker = checker


@pytest.fixture(autouse=True)
def doctest_setup(request, doctest_namespace, tmp_path, monkeypatch):
    doctest_namespace['create_tree'] = create_tree
    doctest_namespace['sample_tree'] = str(sample_tree)
    monkeypatch.syspath_prepend(str(sample_tree.joinpath('zippedmodules.zip')))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'stderr', RedirectToStdout())
    yield
    linecache.clearcache()
