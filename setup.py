#!/usr/bin/env python
import ast
import email.utils
import os
import re

from setuptools import setup


def read(filename):
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return f.read()


metadata = dict(
    (k, ast.literal_eval(v)) for k, v in
    re.findall('^(__version__|__author__|__url__|__licence__) = (.*)$',
               read('findimports.py'), flags=re.MULTILINE)
)
version = metadata['__version__']
author, author_email = email.utils.parseaddr(metadata['__author__'])
url = metadata['__url__']
licence = metadata['__licence__']


setup(
    name='findimports',
    version=version,
    author=author,
    author_email=author_email,
    url=url,
    description='Python module import analysis tool',
    long_description=read('README.rst') + '\n\n' + read('CHANGES.rst'),
    long_description_content_type='text/x-rst',
    license=licence,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ] + [
        'License :: OSI Approved :: GNU General Public License (GPL)'
            if licence.startswith('GPL') else
        'License :: OSI Approved :: MIT License'
            if licence.startswith('MIT') else
        'License :: uhh, dunno',
    ],
    python_requires='>=3.7',

    py_modules=['findimports'],
    test_suite='testsuite',
    zip_safe=False,
    entry_points="""
    [console_scripts]
    findimports = findimports:main
    """,
)
