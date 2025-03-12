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

import datetime
import os
import sys
import random
import glob
import logging
import ftplib

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
class TestFtpHandler(FtpBackupTestcase):

    # -------------------------------------------------------------------------
    def setUp(self):
        pass

    # -------------------------------------------------------------------------
    def tearDown(self):
        pass

    # -------------------------------------------------------------------------
    def test_import_ftp_dir(self):
        """"Test importing ftp_backup.ftp_dir."""
        LOG.info(self.get_method_doc())

        import ftp_backup.ftp_dir
        LOG.debug('Version of ftp_backup.ftp_dir: {!r}'.format(
            ftp_backup.ftp_dir.__version__))

    # -------------------------------------------------------------------------
    def test_dir_entry(self):
        """Test creating directory entry objects."""
        LOG.info(self.get_method_doc())

        cur_year = datetime.date.today().year

        test_data = (
            {   'line': (
                    'drwx---r-x   2 b082473  cust         8192 '
                    'Jan  1  2014 backup-dir.2014-01-01_00'),
                'group': 'cust',
                'is_dir': True,
                'is_file': False,
                'mtime': datetime.datetime(2014, 1, 1, 0, 0),
                'name': 'backup-dir.2014-01-01_00',
                'num_hardlinks': 2,
                'permissions': 'drwx---r-x',
                'perms_octal': '0o1705',
                'size': 8192,
                'user': 'b082473',
            },
            {   'line': (
                    '-rw-r--r--   1 b082473  cust      1234567 '
                    'May  1 08:20 backup file 2015-05-01_00'),
                'group': 'cust',
                'is_dir': False,
                'is_file': True,
                'mtime': datetime.datetime(cur_year, 5, 1, 8, 20),
                'name': 'backup file 2015-05-01_00',
                'num_hardlinks': 1,
                'permissions': '-rw-r--r--',
                'perms_octal': '0o0644',
                'size': 1234567,
                'user': 'b082473',
            },
        )

        from ftp_backup.ftp_dir import DirEntry

        for test_entry in test_data:

            line = test_entry['line']
            LOG.debug("Testing line: " + line)

            entry = DirEntry.from_dir_line(line, appname=self.appname, verbose=self.verbose)
            LOG.debug("DirEntry: {!r}".format(entry))
            if self.verbose > 1:
                LOG.debug('DirEntry:\n' + pp(entry.as_dict()))
            if self.verbose > 2:
                LOG.debug('Expected values::\n' + pp(test_entry))
            self.assertEqual(entry.group, test_entry['group'])
            self.assertEqual(entry.is_dir(), test_entry['is_dir'])
            self.assertEqual(entry.is_file(), test_entry['is_file'])
            self.assertEqual(entry.mtime, test_entry['mtime'])
            self.assertEqual(entry.name, test_entry['name'])
            self.assertEqual(entry.num_hardlinks, test_entry['num_hardlinks'])
            self.assertEqual(str(entry.perms), test_entry['permissions'])
            self.assertEqual(entry.perms.oct(), test_entry['perms_octal'])
            self.assertEqual(entry.size, test_entry['size'])
            self.assertEqual(entry.user, test_entry['user'])

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
    suite.addTest(TestFtpHandler('test_dir_entry', verbose))
    # suite.addTest(TestFtpHandler('test_import_ftp_handler', verbose))
    # suite.addTest(TestFtpHandler('test_handler_object', verbose))
    # suite.addTest(TestFtpHandler('test_handler_object_tls', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4



