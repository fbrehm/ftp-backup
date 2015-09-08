#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@license: GPL3
@summary: Application class for script for backing up a directory to a FTP server
"""

# Standard modules
import logging
import textwrap
import os

# Third party modules

# Own modules
from pb_base.common import to_bool
from pb_base.app import PbApplicationError

from pb_base.cfg_app import PbCfgAppError
from pb_base.cfg_app import PbCfgApp

import ftp_backup

__version__ = '0.1.0'

LOG = logging.getLogger(__name__)
DEFAULT_FTP_PORT = 21
DEFAULT_FTP_USER = 'anonymous'
DEFAULT_FTP_PWD = 'frank@brehm-online.com'
DEFAULT_FTP_PASSIVE = False
DEFAULT_FTP_DIR = '/backup'
DEFAULT_FTP_TZ = 'UTC'

DEFAULT_LOCAL_DIRECTORY = os.sep + os.path.join('var', 'backup')

DEFAULT_COPIES_YEARLY = 2
DEFAULT_COPIES_MONTHLY = 2
DEFAULT_COPIES_WEEKLY = 2
DEFAULT_COPIES_DAILY = 2


# =============================================================================
class BackupByFtpApp(PbCfgApp):
    """Application class for backing up a directory to a FTP server."""

    # -------------------------------------------------------------------------
    def __init__(self, appname=None, verbose=0):
        """Constructor."""

        description = """\
        Performs a backup of all regular file in a dedicated local directory
        to a subdirectory on a FTP server, where a distinct number of old
        backup directories on the FTP server should be stalled.
        """

        self.ftp_host = 'ftp'
        self.ftp_port = DEFAULT_FTP_PORT
        self.ftp_user = DEFAULT_FTP_USER
        self.ftp_password = DEFAULT_FTP_PWD
        self.ftp_passive = DEFAULT_FTP_PASSIVE
        self.ftp_remote_dir = DEFAULT_FTP_DIR
        self.ftp_tz = DEFAULT_FTP_TZ

        self.local_directory = DEFAULT_LOCAL_DIRECTORY

        self.copies = {
            'yearly': DEFAULT_COPIES_YEARLY,
            'monthly': DEFAULT_COPIES_MONTHLY,
            'weekly': DEFAULT_COPIES_WEEKLY,
            'daily': DEFAULT_COPIES_DAILY,
        }

        super(BackupByFtpApp, self).__init__(
            appname=appname,
            verbose=verbose,
            version=ftp_backup.__version__,
            description = textwrap.dedent(description),
            cfg_dir='ftp-backup',
            hide_default_config=True,
            need_config_file=False,
        )
        self.post_init()

        self.initialized = True

    # -------------------------------------------------------------------------
    def init_arg_parser(self):

        super(BackupByFtpApp, self).init_arg_parser()

        h = "Local directory for the files to backup (default: %r)." % (DEFAULT_LOCAL_DIRECTORY)
        self.arg_parser.add_argument('-D', '--dir', '--local-dir', metavar='DIR',
            dest='local_dir', help = h)

        ftp_group = self.arg_parser.add_argument_group('FTP parameters')

        h = 'The FTP server, where to upload the backup files.'
        ftp_group.add_argument('--host', metavar='HOST', help=h)

        h = "The TCP port on the FTP server of the listening FTP daemon (default: %d)." % (
            DEFAULT_FTP_PORT)
        ftp_group.add_argument('--port', metavar='PORT', type=int, help=h)

        h = 'The username on the FTP server (default: %r).' % (DEFAULT_FTP_PWD)
        ftp_group.add_argument('--user', metavar='USER', help=h)

        h = 'The user password on the FTP server (default: %r).' % (DEFAULT_FTP_PWD)
        ftp_group.add_argument('--password', metavar='PASSWORD', help=h)

        h = 'Use passive mode for FTP transfer (default: %r).' % (DEFAULT_FTP_PASSIVE)
        ftp_group.add_argument('--passive', action='store_true', help=h)

        h = 'The root directory on the FTP server (default: %r).' % (DEFAULT_FTP_DIR)
        ftp_group.add_argument('--remote-dir', metavar='DIR', help=h)

        h = 'The timezone on the FTP server (default: %r).' % (DEFAULT_FTP_TZ)
        ftp_group.add_argument('--tz', help=h)

        copies_group = self.arg_parser.add_argument_group('Backup copies to store')

        copies_group.add_argument('--copies-yearly', type=int, metavar = 'NR',
            help='Yearly (default: %d).' % (DEFAULT_COPIES_YEARLY))

        copies_group.add_argument('--copies-monthly', type=int, metavar = 'NR',
            help='Monthly (default: %d).' % (DEFAULT_COPIES_MONTHLY))

        copies_group.add_argument('--copies-weekly', type=int, metavar = 'NR',
            help='Weekly (default: %d).' % (DEFAULT_COPIES_WEEKLY))

        copies_group.add_argument('--copies-daily', type=int, metavar = 'NR',
            help='Daily (default: %d).' % (DEFAULT_COPIES_DAILY))

    # -------------------------------------------------------------------------
    def perform_arg_parser(self):

        super(BackupByFtpApp, self).perform_arg_parser()

        if self.args.local_dir:
            self.local_directory = self.args.local_dir

        if self.args.host:
            self.ftp_host = self.args.host
        if self.args.port and self.args.port > 0:
            self.ftp_port = self.args.port
        if self.args.user:
            self.ftp_user = self.args.user
        if self.args.password:
            self.ftp_password = self.args.password
        if self.args.passive:
            self.ftp_passive = True
        if self.args.remote_dir:
            self.ftp_remote_dir = self.args.remote_dir
        if self.args.tz:
            self.ftp_tz = self.args.tz

        if self.args.copies_yearly and self.args.copies_yearly > 0:
            self.copies['yearly'] = self.args.copies_yearly
        if self.args.copies_monthly and self.args.copies_monthly > 0:
            self.copies['monthly'] = self.args.copies_monthly
        if self.args.copies_weekly and self.args.copies_weekly > 0:
            self.copies['weekly'] = self.args.copies_weekly
        if self.args.copies_daily and self.args.copies_daily > 0:
            self.copies['daily'] = self.args.copies_daily

    # -------------------------------------------------------------------------
    def perform_config(self):

        super(BackupByFtpApp, self).perform_config()

        int_msg_tpl = "Error in configuration: [%s]/%s %r is not an integer value: %s"

        for section in self.cfg:

            if section.lower() == 'global':
                if 'backup_dir' in self.cfg[section] and not self.args.local_dir:
                    self.local_directory = self.cfg[section]['backup_dir']

            if section.lower() == 'ftp':

                if 'host' in self.cfg[section] and not self.args.host:
                    self.ftp_host = self.cfg[section]['host']
                if 'port' in self.cfg[section] and not self.args.port:
                    p = DEFAULT_FTP_PORT
                    try:
                        p = int(self.cfg[section]['port'])
                    except ValueError as e:
                        msg = int_msg_tpl % ('FTP', 'port', self.cfg[section]['port'], str(e))
                        LOG.error(msg)
                    else:
                        self.ftp_port = p
                if 'user' in self.cfg[section] and not self.args.user:
                    self.ftp_user = self.cfg[section]['user']
                if 'password' in self.cfg[section] and not self.args.password:
                    self.ftp_password = self.cfg[section]['password']
                if 'passive' in self.cfg[section] and not self.args.passive:
                    self.ftp_passive = to_bool(self.cfg[section]['passive'])
                if 'dir' in self.cfg[section] and not self.args.remote_dir:
                    self.ftp_remote_dir = self.cfg[section]['dir']
                if 'timezone' in self.cfg[section] and not self.args.tz:
                    self.ftp_tz = self.cfg[section]['timezone']

            if section.lower() == 'copies':

                if 'yearly' in self.cfg[section] and not self.args.copies_yearly:
                    v = DEFAULT_COPIES_YEARLY
                    try:
                        v = int(self.cfg[section]['yearly'])
                    except ValueError as e:
                        msg = int_msg_tpl % ('Copies', 'yearly', self.cfg[section]['yearly'], str(e))
                    else:
                        self.copies['yearly'] = v

                if 'monthly' in self.cfg[section] and not self.args.copies_monthly:
                    v = DEFAULT_COPIES_MONTHLY
                    try:
                        v = int(self.cfg[section]['monthly'])
                    except ValueError as e:
                        msg = int_msg_tpl % ('Copies', 'monthly', self.cfg[section]['monthly'], str(e))
                    else:
                        self.copies['monthly'] = v

                if 'weekly' in self.cfg[section] and not self.args.copies_weekly:
                    v = DEFAULT_COPIES_WEEKLY
                    try:
                        v = int(self.cfg[section]['weekly'])
                    except ValueError as e:
                        msg = int_msg_tpl % ('Copies', 'weekly', self.cfg[section]['weekly'], str(e))
                    else:
                        self.copies['weekly'] = v

                if 'daily' in self.cfg[section] and not self.args.copies_daily:
                    v = DEFAULT_COPIES_DAILY
                    try:
                        v = int(self.cfg[section]['daily'])
                    except ValueError as e:
                        msg = int_msg_tpl % ('Copies', 'daily', self.cfg[section]['daily'], str(e))
                    else:
                        self.copies['daily'] = v

    # -------------------------------------------------------------------------
    def _run(self):
        """The underlaying startpoint of the application."""

        LOG.info("Da da da...")


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
