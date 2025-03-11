#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@summary: General used functions and objects used for unit tests on the ftp handler class.

@author: Frank Brehm
@contact: frank@brehm-online.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2025 by Profitbricks GmbH
@license: GPL3
"""

import argparse
import logging
import os
import sys
import tempfile
import textwrap

try:
    import unittest2 as unittest
except ImportError:
    import unittest

# Own modules

from fb_logging.colored import ColoredFormatter

from fb_tools.common import to_str

# =============================================================================

LOG = logging.getLogger(__name__)


# =============================================================================
def get_arg_verbose():
    """Get and return command line arguments."""
    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument(
        "-v", "--verbose", action="count",
        dest='verbose', help='Increase the verbosity level')
    args = arg_parser.parse_args()

    return args.verbose


# =============================================================================
def init_root_logger(verbose=0):
    """Initialize the root logger."""
    root_log = logging.getLogger()
    root_log.setLevel(logging.WARNING)
    if verbose:
        root_log.setLevel(logging.INFO)
        if verbose > 1:
            root_log.setLevel(logging.DEBUG)

    appname = os.path.basename(sys.argv[0])
    if verbose > 1:
        format_str = '[%(asctime)s]: ' + appname + ': '
    else:
        format_str = appname + ': '
    if verbose:
        if verbose > 1:
            format_str += '%(name)s(%(lineno)d) %(funcName)s() '
        else:
            format_str += '%(name)s '
    format_str += '%(levelname)s - %(message)s'
    formatter = None
    formatter = ColoredFormatter(format_str)

    # create log handler for console output
    lh_console = logging.StreamHandler(sys.stderr)
    if verbose:
        lh_console.setLevel(logging.DEBUG)
    else:
        lh_console.setLevel(logging.INFO)
    lh_console.setFormatter(formatter)

    root_log.addHandler(lh_console)


# =============================================================================
def currentFuncName(n=0):
    """Return the name of the function, from where this function was called."""
    return sys._getframe(n + 1).f_code.co_name


# =============================================================================
class FtpBackupTestcase(unittest.TestCase):

    # -------------------------------------------------------------------------
    def __init__(self, methodName='runTest', verbose=0):
        """Initialize the base testcase class."""
        self._verbose = int(verbose)

        appname = os.path.basename(sys.argv[0]).replace('.py', '')
        self._appname = appname

        super(FtpBackupTestcase, self).__init__(methodName)

    # -------------------------------------------------------------------------
    @property
    def verbose(self):
        """Return the verbosity level."""
        return getattr(self, '_verbose', 0)

    # -------------------------------------------------------------------------
    @property
    def appname(self):
        """Return the name of the current running application."""
        return self._appname

    # -------------------------------------------------------------------------
    def setUp(self):
        """Execute this on seting up before calling each particular test method."""
        pass

    # -------------------------------------------------------------------------
    def tearDown(self):
        """Tear down routine for calling each particular test method."""
        pass

    # -------------------------------------------------------------------------
    @classmethod
    def current_function_name(cls, level=0):
        """Return the name of the function, from where this method was called."""
        return sys._getframe(level + 1).f_code.co_name

    # -------------------------------------------------------------------------
    @classmethod
    def get_method_doc(cls):
        """Return the docstring of the method, from where this method was called."""
        func_name = cls.current_function_name(1)
        doc_str = getattr(cls, func_name).__doc__
        cname = cls.__name__
        mname = '{cls}.{meth}()'.format(cls=cname, meth=func_name)
        msg = 'This is {}.'.format(mname)
        if doc_str is None:
            return msg
        doc_str = textwrap.dedent(doc_str).strip()
        if doc_str:
            msg = '{m} - {d}'.format(m=mname, d=doc_str)
        return msg


# =============================================================================

if __name__ == '__main__':

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
