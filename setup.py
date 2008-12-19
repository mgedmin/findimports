#!/usr/bin/env python
import os
from setuptools import setup, find_packages

from findimports import __version__

readme = os.path.join(os.path.dirname(__file__), 'README.txt')

setup(
    name='findimports',
    version=__version__,
    author='Marius Gedminas',
    author_email='marius@gedmin.as',
    url='https://launchpad.net/findimports',
    download_url='http://pypi.python.org/pypi/findimports',
    description='Python module import analysis tool',
    long_description=readme,
    license='GPL',

    py_modules=['findimports'],
    zip_safe=False,
    entry_points="""
    [console_scripts]
    findimports = findimports:main
    """,
)
