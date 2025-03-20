#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on ftp directory object
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
class TestFtpDir(FtpBackupTestcase):

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

        LOG.info('Testing import of DirEntry from ftp_backup.ftp_dir ...')
        from ftp_backup.ftp_dir import DirEntry
        LOG.debug('Description of DirEntry: ' + textwrap.dedent(DirEntry.__doc__))

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

# =============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    LOG.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestFtpDir('test_import_ftp_dir', verbose))
    suite.addTest(TestFtpDir('test_dir_entry', verbose))

    runner = unittest.TextTestRunner(verbosity=verbose)

    result = runner.run(suite)

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4



