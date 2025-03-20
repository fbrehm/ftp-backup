#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2025 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on ftp handler object
'''

import datetime
import os
import sys
import random
import glob
import logging
import ftplib
import textwrap

from ftplib import FTP, FTP_TLS

# Own modules
from fb_tools.common import to_bool, pp, bytes2human
# from fb_tools.common import to_utf8_or_bust as to_utf8

try:
    import unittest2 as unittest
except ImportError:
    import unittest

# from mock import MagicMock

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..', 'lib'))
sys.path.insert(0, libdir)

from general import FtpBackupTestcase, get_arg_verbose, init_root_logger

MY_APPNAME = os.path.basename(sys.argv[0]).replace('.py', '')
LOG = logging.getLogger(MY_APPNAME)


# =============================================================================
class TestSftpHandler(FtpBackupTestcase):

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def tearDown(self):
        pass

    # -------------------------------------------------------------------------
    def test_import_sftp_handler(self):
        """"Test importing ftp_backup.sftp_handler."""
        LOG.info(self.get_method_doc())

        import ftp_backup.sftp_handler
        LOG.debug('Version of ftp_backup.sftp_handler: {!r}'.format(
            ftp_backup.sftp_handler.__version__))

        LOG.info('Testing import of SFTPHandler from ftp_backup.sftp_handler ...')
        from ftp_backup.sftp_handler import SFTPHandler
        LOG.debug('Description of SFTPHandler: ' + textwrap.dedent(SFTPHandler.__doc__))

    # -------------------------------------------------------------------------
    def test_handler_object(self):
        """Testing init of a FTP handler object."""
        LOG.info(self.get_method_doc())

        from ftp_backup.sftp_handler import SFTPHandler
        from ftp_backup.sftp_handler import DEFAULT_SSH_SERVER
        from ftp_backup.sftp_handler import DEFAULT_SSH_PORT
        from ftp_backup.sftp_handler import DEFAULT_SSH_USER
        from ftp_backup.sftp_handler import DEFAULT_REMOTE_DIR
        from ftp_backup.sftp_handler import DEFAULT_SSH_TIMEOUT
        from ftp_backup.sftp_handler import DEFAULT_SSH_KEY

        sftp = SFTPHandler(
            appname=self.appname,
            verbose=self.verbose,
        )

        if self.verbose > 1:
            LOG.debug("repr of SFTPHandler object: %r", sftp)

        if self.verbose > 2:
            LOG.debug("SFTPHandler object:\n%s", pp(sftp.as_dict(True)))

        LOG.info("Checking SFTP handler object for default values ...")
        self.assertEqual(sftp.connected, False)
        self.assertEqual(sftp.host, DEFAULT_SSH_SERVER)
        self.assertEqual(sftp.port, DEFAULT_SSH_PORT)
        self.assertIsNone(sftp.remote_dir)
        self.assertEqual(sftp.start_remote_dir, DEFAULT_REMOTE_DIR)
        self.assertEqual(sftp.timeout, DEFAULT_SSH_TIMEOUT)
        self.assertEqual(sftp.user, DEFAULT_SSH_USER)


# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestSftpHandler('test_import_sftp_handler', verbose))
    suite.addTest(TestSftpHandler('test_handler_object', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)


# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4



