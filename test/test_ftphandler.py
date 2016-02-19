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
import ftplib

from ftplib import FTP, FTP_TLS

# Own modules
from pb_base.common import to_bool, pp, bytes2human
from pb_base.common import to_utf8_or_bust as to_utf8

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import MagicMock

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..', 'lib'))
sys.path.insert(0, libdir)

from general import FtpBackupTestcase, get_arg_verbose, init_root_logger

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
        from ftp_backup.ftp_handler import DEFAULT_FTP_HOST
        from ftp_backup.ftp_handler import DEFAULT_FTP_PORT
        from ftp_backup.ftp_handler import DEFAULT_FTP_USER
        from ftp_backup.ftp_handler import DEFAULT_FTP_PWD
        from ftp_backup.ftp_handler import DEFAULT_FTP_TZ
        from ftp_backup.ftp_handler import DEFAULT_FTP_TIMEOUT
        from ftp_backup.ftp_handler import DEFAULT_MAX_STOR_ATTEMPTS
        from ftp_backup.ftp_handler import MAX_FTP_TIMEOUT

        ftp = FTPHandler(
            appname=self.appname,
            verbose=self.verbose,
        )

        if self.verbose > 1:
            LOG.debug("repr of FTPHandler object: %r", ftp)

        if self.verbose > 2:
            LOG.debug("FTPHandler object:\n%s", pp(ftp.as_dict(True)))

        LOG.info("Checking FTP handler object for default values ...")
        self.assertIsInstance(ftp.ftp, FTP)
        self.assertEqual(ftp.connected, False)
        self.assertEqual(ftp.host, DEFAULT_FTP_HOST)
        self.assertEqual(ftp.logged_in, False)
        self.assertEqual(ftp.max_stor_attempts, DEFAULT_MAX_STOR_ATTEMPTS)
        self.assertEqual(ftp.passive, False)
        self.assertEqual(ftp.password, DEFAULT_FTP_PWD)
        self.assertEqual(ftp.port, DEFAULT_FTP_PORT)
        self.assertEqual(ftp.remote_dir, '/')
        self.assertEqual(ftp.timeout, DEFAULT_FTP_TIMEOUT)
        self.assertEqual(ftp.tls, False)
        self.assertEqual(ftp.tz, DEFAULT_FTP_TZ)
        self.assertEqual(ftp.user, DEFAULT_FTP_USER)

    # -------------------------------------------------------------------------
    def test_handler_object_tls(self):

        LOG.info("Testing init of a FTP handler object with TLS support ...")

        from ftp_backup.ftp_handler import FTPHandler

        ftp = FTPHandler(
            appname=self.appname,
            tls=True,
            verbose=self.verbose,
        )

        if self.verbose > 1:
            LOG.debug("repr of FTPHandler object: %r", ftp)

        if self.verbose > 2:
            LOG.debug("FTPHandler object:\n%s", pp(ftp.as_dict(True)))

        LOG.info("Checking FTP handler object for default values ...")
        self.assertIsInstance(ftp.ftp, FTP_TLS)
        self.assertEqual(ftp.tls, True)
        self.assertEqual(ftp.tls_verify, None)

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
    suite.addTest(TestFtpHandler('test_handler_object_tls', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4



