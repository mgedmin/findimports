# -*- coding: utf-8 -*-
import gc

def eat():
    gc.collect()

def doctest_with_unicode():
    u"""regression test:

        >>> s = u"ünicøde doctests do not break findimports"

    """
