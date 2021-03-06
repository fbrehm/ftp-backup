#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@license: GPL3
@summary: Application class for script for backing up a directory to a SSH server
"""

# Standard modules
import sys
import logging
import textwrap
import os
import ssl
import re
import glob
import time
import socket

from datetime import datetime

from pathlib import PurePosixPath, PosixPath

# Third party modules
import six

# Own modules
from pb_logging.colored import ColoredFormatter

from pb_base.common import to_bool, pp, bytes2human

from pb_base.handler import PbBaseHandlerError

from pb_base.cfg_app import PbCfgApp

import ftp_backup
from ftp_backup import DEFAULT_LOCAL_DIRECTORY
from ftp_backup import DEFAULT_COPIES_YEARLY, DEFAULT_COPIES_MONTHLY
from ftp_backup import DEFAULT_COPIES_WEEKLY, DEFAULT_COPIES_DAILY

from ftp_backup.sftp_handler import SFTPHandlerError, SFTPLocalPathError
from ftp_backup.sftp_handler import SFTPHandler
from ftp_backup.sftp_handler import DEFAULT_SSH_SERVER, DEFAULT_SSH_PORT
from ftp_backup.sftp_handler import DEFAULT_SSH_USER, DEFAULT_REMOTE_DIR
from ftp_backup.sftp_handler import DEFAULT_SSH_TIMEOUT, DEFAULT_SSH_KEY

__version__ = '0.4.6'

LOG = logging.getLogger(__name__)

APP_VERSION = ftp_backup.__version__
try:
    import ftp_backup.local_version
    APP_VERSION = ftp_backup.local_version.__version__
except ImportError:
    pass


# =============================================================================
class SFTPHandlerError(PbBaseHandlerError):
    pass


# =============================================================================
class BackupBySftpApp(PbCfgApp):
    """Application class for backing up a directory to a SSH server."""

    # -------------------------------------------------------------------------
    def __init__(self, appname=None, verbose=0):

        """Constructor."""

        description = """\
        Performs a backup of all regular file in a dedicated local directory
        to a subdirectory via SFTP on a SSH server, where a distinct number of old
        backup directories on the SSH server should be stalled.
        """

        self.handler = SFTPHandler(appname=appname, verbose=verbose, initialized=False,
            base_dir=str(DEFAULT_LOCAL_DIRECTORY))

        super(BackupBySftpApp, self).__init__(
            appname=appname,
            base_dir=str(DEFAULT_LOCAL_DIRECTORY),
            verbose=verbose,
            version=APP_VERSION,
            description=textwrap.dedent(description),
            cfg_dir='ftp-backup',
            hide_default_config=True,
            need_config_file=False,
        )
        self.post_init()

        self.initialized = True

    # -------------------------------------------------------------------------
    def __del__(self):

        self.handler = None

    # -------------------------------------------------------------------------
    def init_arg_parser(self):

        super(BackupBySftpApp, self).init_arg_parser()

        h = "Local directory for the files to backup (default: %r)." % (
            DEFAULT_LOCAL_DIRECTORY)
        self.arg_parser.add_argument(
            '-D', '--dir', '--local-dir', metavar='DIR', dest='local_dir', help=h)

        h = "Simulation mode, no modifying actions are done."
        self.arg_parser.add_argument('-t', '--test', action='store_true', help=h)

        ssh_group = self.arg_parser.add_argument_group('SSH/SFTP parameters')

        h = 'The SSH server, where to upload the backup files (default: %r).' % (
            DEFAULT_SSH_SERVER)
        ssh_group.add_argument('--host', metavar='HOST', help=h)

        h = "The TCP port on the SSH server of the listening sshd (default: %d)." % (
            DEFAULT_SSH_PORT)
        ssh_group.add_argument('--port', metavar='PORT', type=int, help=h)

        h = 'The username on the SSH server (default: %r).' % (DEFAULT_SSH_USER)
        ssh_group.add_argument('--user', metavar='USER', help=h)

        h = "The private SSH key file to use for connecting to the SSH server (default: %r)." % (
            str(DEFAULT_SSH_KEY))
        ssh_group.add_argument('-K', '--ssh-key', metavar='FILE', help=h)

        h = 'The root directory on the SSH server (default: %r).' % (str(DEFAULT_REMOTE_DIR))
        ssh_group.add_argument('--remote-dir', metavar='DIR', help=h)

        copies_group = self.arg_parser.add_argument_group('Backup copies to store')

        copies_group.add_argument(
            '--copies-yearly', type=int, metavar='NR',
            help='Yearly (default: %d).' % (DEFAULT_COPIES_YEARLY))

        copies_group.add_argument(
            '--copies-monthly', type=int, metavar='NR',
            help='Monthly (default: %d).' % (DEFAULT_COPIES_MONTHLY))

        copies_group.add_argument(
            '--copies-weekly', type=int, metavar='NR',
            help='Weekly (default: %d).' % (DEFAULT_COPIES_WEEKLY))

        copies_group.add_argument(
            '--copies-daily', type=int, metavar='NR',
            help='Daily (default: %d).' % (DEFAULT_COPIES_DAILY))

    # -------------------------------------------------------------------------
    def perform_arg_parser(self):

        super(BackupBySftpApp, self).perform_arg_parser()
        self.handler.verbose = self.verbose
        self.handler.base_dir = self.base_dir

        if self.args.local_dir:
            self.base_dir = self.args.local_dir
            self.handler.local_dir = self.args.local_dir

        if self.args.host:
            self.handler.host = self.args.host

        if self.args.port and self.args.port > 0:
            self.handler.port = self.args.port

        if self.args.user:
            self.handler.user = self.args.user

        if self.args.remote_dir:
            self.start_remote_dir = PurePosixPath(self.args.remote_dir)

        if self.args.ssh_key:
            self.handler.key_file = self.args.ssh_key

        if self.args.test:
            self.handler.simulate = True

        if self.args.copies_yearly and self.args.copies_yearly > 0:
            self.handler.copies['yearly'] = self.args.copies_yearly
        if self.args.copies_monthly and self.args.copies_monthly > 0:
            self.handler.copies['monthly'] = self.args.copies_monthly
        if self.args.copies_weekly and self.args.copies_weekly > 0:
            self.handler.copies['weekly'] = self.args.copies_weekly
        if self.args.copies_daily and self.args.copies_daily > 0:
            self.handler.copies['daily'] = self.args.copies_daily

    # -------------------------------------------------------------------------
    def init_logging(self):
        """
        Initialize the logger object.
        It creates a colored loghandler with all output to STDERR.
        Maybe overridden in descendant classes.

        @return: None
        """

        root_log = logging.getLogger()
        root_log.setLevel(logging.INFO)
        if self.verbose:
            root_log.setLevel(logging.DEBUG)

        # create formatter
        format_str = '[%(asctime)s]: ' + self.appname + ': '
        if self.verbose:
            if self.verbose > 1:
                format_str += '%(name)s(%(lineno)d) %(funcName)s() '
            else:
                format_str += '%(name)s '
        format_str += '%(levelname)s - %(message)s'
        formatter = None
        if self.terminal_has_colors:
            formatter = ColoredFormatter(format_str)
        else:
            formatter = logging.Formatter(format_str)

        # create log handler for console output
        lh_console = logging.StreamHandler(sys.stderr)
        if self.verbose:
            lh_console.setLevel(logging.DEBUG)
        else:
            lh_console.setLevel(logging.INFO)
        lh_console.setFormatter(formatter)

        root_log.addHandler(lh_console)

        return

    # -------------------------------------------------------------------------
    def perform_config(self):

        super(BackupBySftpApp, self).perform_config()

        int_msg_tpl = "Error in configuration: [%s]/%s %r is not an integer value: %s"

        for section in self.cfg:

            if section.lower() == 'global':
                if 'backup_dir' in self.cfg[section] and not self.args.local_dir:
                    self.base_dir = self.cfg[section]['backup_dir']
                    self.handler.local_dir = self.cfg[section]['backup_dir']

            if section.lower() == 'sftp' or section.lower() == 'scp':

                if 'host' in self.cfg[section] and not self.args.host:
                    self.handler.host = self.cfg[section]['host']

                if 'port' in self.cfg[section] and not self.args.port:
                    p = DEFAULT_SSH_PORT
                    try:
                        p = int(self.cfg[section]['port'])
                    except ValueError as e:
                        msg = int_msg_tpl % ('SFTP', 'port', self.cfg[section]['port'], str(e))
                        LOG.error(msg)
                    else:
                        self.handler.port = p

                if 'timeout' in self.cfg[section]:
                    try:
                        timeout = int(self.cfg[section]['timeout'])
                    except ValueError as e:
                        msg = int_msg_tpl % ('SFTP', 'timeout', self.cfg[section]['timeout'], str(e))
                        LOG.error(msg)
                    else:
                        self.handler.timeout = timeout

                if 'user' in self.cfg[section] and not self.args.user:
                    self.handler.user = self.cfg[section]['user']

                if 'dir' in self.cfg[section] and not self.args.remote_dir:
                    self.handler.start_remote_dir = PurePosixPath(self.cfg[section]['dir'])

                if 'key_file' in self.cfg[section] and not self.args.ssh_key:
                    self.handler.key_file = self.cfg[section]['key_file']

            if section.lower() == 'copies':

                if 'yearly' in self.cfg[section] and not self.args.copies_yearly:
                    v = DEFAULT_COPIES_YEARLY
                    try:
                        v = int(self.cfg[section]['yearly'])
                    except ValueError as e:
                        msg = int_msg_tpl % (
                            'Copies', 'yearly', self.cfg[section]['yearly'], str(e))
                    else:
                        self.handler.copies['yearly'] = v

                if 'monthly' in self.cfg[section] and not self.args.copies_monthly:
                    v = DEFAULT_COPIES_MONTHLY
                    try:
                        v = int(self.cfg[section]['monthly'])
                    except ValueError as e:
                        msg = int_msg_tpl % (
                            'Copies', 'monthly', self.cfg[section]['monthly'], str(e))
                    else:
                        self.handler.copies['monthly'] = v

                if 'weekly' in self.cfg[section] and not self.args.copies_weekly:
                    v = DEFAULT_COPIES_WEEKLY
                    try:
                        v = int(self.cfg[section]['weekly'])
                    except ValueError as e:
                        msg = int_msg_tpl % (
                            'Copies', 'weekly', self.cfg[section]['weekly'], str(e))
                    else:
                        self.handler.copies['weekly'] = v

                if 'daily' in self.cfg[section] and not self.args.copies_daily:
                    v = DEFAULT_COPIES_DAILY
                    try:
                        v = int(self.cfg[section]['daily'])
                    except ValueError as e:
                        msg = int_msg_tpl % ('Copies', 'daily', self.cfg[section]['daily'], str(e))
                    else:
                        self.handler.copies['daily'] = v

    # -------------------------------------------------------------------------
    def pre_run(self):

        super(BackupBySftpApp, self).pre_run()

        paramiko_logger = logging.getLogger('paramiko.transport')
        if self.verbose < 1:
            paramiko_logger.setLevel(logging.WARNING)
        elif self.verbose < 2:
            paramiko_logger.setLevel(logging.INFO)

    # -------------------------------------------------------------------------
    def _run(self):
        """The underlaying startpoint of the application."""

        re_whitespace = re.compile(r'\s+')

        try:
            self.handler.connect()
        except(PermissionError, SFTPLocalPathError) as e:
            self.exit(1, str(e))

        LOG.info("Starting ...")

        subdir = socket.gethostname()

        try:
            if self.handler.exists(subdir):
                LOG.debug("Remote file %r exists.", subdir)
                if self.handler.is_dir(subdir):
                    LOG.debug("Remote file %r is a directory.", subdir)
                else:
                    msg = "Remote file %r is NOT a directory." % (subdir)
                    self.exit(5, msg)
            else:
                LOG.warn("Remote file %r does not exists.", subdir)
                self.handler.mkdir(subdir)

            self.handler.remote_dir = subdir
            subdir = self.handler.remote_dir
            LOG.info("Current main remote directory is now %r.", str(self.handler.remote_dir))

            self.handler.cleanup_old_backupdirs()
            self.handler.do_backup()
            self.handler.remote_dir = subdir
            self.handler.show_disk_usage()

        finally:
            self.handler.disconnect()

    # -------------------------------------------------------------------------
    def post_run(self):
        """
        Function to run after the main routine.

        """

        self.handler = None

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
