#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on ftp handler object
'''

import os
import sys
import random
import glob
import logging

try:
    import unittest2 as unittest
except ImportError:
    import unittest

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..', 'lib'))
sys.path.insert(0, libdir)

from general import FtpBackupTestcase, get_arg_verbose, init_root_logger

from pb_base.common import to_utf8_or_bust as to_utf8

MY_APPNAME = os.path.basename(sys.argv[0]).replace('.py', '')
LOG = logging.getLogger(MY_APPNAME)



# =============================================================================
class TestFtpHandler(FtpBackupTestcase):

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def tearDown(self):
        pass

    # -------------------------------------------------------------------------
    def test_import_ftp_dir(self):

        LOG.info("Test importing ftp_backup.ftp_dir ...")

        import ftp_backup.ftp_dir                                       # noqa

    # -------------------------------------------------------------------------
    def test_import_ftp_handler(self):

        LOG.info("Test importing ftp_backup.ftp_handler ...")

        import ftp_backup.ftp_handler                                   # noqa

    # -------------------------------------------------------------------------
    def test_handler_object(self):

        LOG.info("Testing init of a FTP handler object ...")

        from ftp_backup.ftp_handler import FTPHandler

        ftp = FTPHandler(
            appname=self.appname,
            verbose=self.verbose,
        )

        if self.verbose > 1:
            log.debug("repr of FTPHandler object: %r", ftp)

        if self.verbose > 2:
            log.debug("FTPHandler object:\n%s", pp(ftp.as_dict(True)))



# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestFtpHandler('test_import_ftp_dir', verbose))
    suite.addTest(TestFtpHandler('test_import_ftp_handler', verbose))
    suite.addTest(TestFtpHandler('test_handler_object', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4



