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
import sys
import logging
import textwrap
import os
import ftplib
import ssl
import re
import glob
import time
from datetime import datetime

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

from ftp_backup.ftp_dir import DirEntry

__version__ = '0.4.2'

LOG = logging.getLogger(__name__)
DEFAULT_FTP_PORT = 21
DEFAULT_FTP_USER = 'anonymous'
DEFAULT_FTP_PWD = 'frank@brehm-online.com'
DEFAULT_FTP_PASSIVE = False
DEFAULT_FTP_DIR = '/backup'
DEFAULT_FTP_TZ = 'UTC'

DEFAULT_FTP_TIMEOUT = 60

APP_VERSION = ftp_backup.__version__
try:
    import ftp_backup.local_version
    APP_VERSION = ftp_backup.local_version.__version__
except ImportError:
    pass


# =============================================================================
class FTPHandlerError(PbBaseHandlerError):
    pass


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
        self.ftp_tls = False
        self.ftp_timeout = DEFAULT_FTP_TIMEOUT

        self.simulate = False

        self.connected = False
        self.logged_in = False

        self.ftp = None

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
            version=APP_VERSION,
            description=textwrap.dedent(description),
            cfg_dir='ftp-backup',
            hide_default_config=True,
            need_config_file=False,
        )
        self.post_init()

        self.init_ftp()

        self.initialized = True

    # -------------------------------------------------------------------------
    def __del__(self):

        if self.ftp and self.connected:
            self.ftp.quit()

        self.ftp = None

    # -------------------------------------------------------------------------
    def init_arg_parser(self):

        super(BackupByFtpApp, self).init_arg_parser()

        h = "Local directory for the files to backup (default: %r)." % (DEFAULT_LOCAL_DIRECTORY)
        self.arg_parser.add_argument(
            '-D', '--dir', '--local-dir', metavar='DIR', dest='local_dir', help=h)

        h = "Simulation mode, no modifying actions are done."
        self.arg_parser.add_argument('-t', '--test', action='store_true', help=h)

        ftp_group = self.arg_parser.add_argument_group('FTP parameters')

        h = 'The FTP server, where to upload the backup files.'
        ftp_group.add_argument('--host', metavar='HOST', help=h)

        h = "The TCP port on the FTP server of the listening FTP daemon (default: %d)." % (
            DEFAULT_FTP_PORT)
        ftp_group.add_argument('--port', metavar='PORT', type=int, help=h)

        h = "Use TLS for communication with the FTP server (default: False)."
        ftp_group.add_argument('--tls', action='store_true', help=h)

        h = 'The username on the FTP server (default: %r).' % (DEFAULT_FTP_USER)
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

        super(BackupByFtpApp, self).perform_arg_parser()

        if self.args.local_dir:
            self.local_directory = self.args.local_dir

        if self.args.host:
            self.ftp_host = self.args.host
        if self.args.port and self.args.port > 0:
            self.ftp_port = self.args.port
        if self.args.tls:
            self.ftp_tls = True
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

        if self.args.test:
            self.simulate = True

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
                if 'tls' in self.cfg[section] and not self.args.tls:
                    self.ftp_tls = to_bool(self.cfg[section]['tls'])
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
                        msg = int_msg_tpl % (
                            'Copies', 'yearly', self.cfg[section]['yearly'], str(e))
                    else:
                        self.copies['yearly'] = v

                if 'monthly' in self.cfg[section] and not self.args.copies_monthly:
                    v = DEFAULT_COPIES_MONTHLY
                    try:
                        v = int(self.cfg[section]['monthly'])
                    except ValueError as e:
                        msg = int_msg_tpl % (
                            'Copies', 'monthly', self.cfg[section]['monthly'], str(e))
                    else:
                        self.copies['monthly'] = v

                if 'weekly' in self.cfg[section] and not self.args.copies_weekly:
                    v = DEFAULT_COPIES_WEEKLY
                    try:
                        v = int(self.cfg[section]['weekly'])
                    except ValueError as e:
                        msg = int_msg_tpl % (
                            'Copies', 'weekly', self.cfg[section]['weekly'], str(e))
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
    def init_ftp(self):

        LOG.debug("Initializing FTP object ...")
        if not self.ftp_tls:
            self.ftp = ftplib.FTP(timeout=self.ftp_timeout)
        else:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_NONE
            self.ftp = ftplib.FTP_TLS(context=context, timeout=self.ftp_timeout)

        if self.verbose > 1:
            if self.verbose > 2:
                self.ftp.set_debuglevel(2)
            else:
                self.ftp.set_debuglevel(1)

    # -------------------------------------------------------------------------
    def login_ftp(self):

        LOG.info("Connecting to FTP server %r (port %d) ...", self.ftp_host, self.ftp_port)
        self.ftp.connect(host=self.ftp_host, port=self.ftp_port)
        self.connected = True

        msg = self.ftp.getwelcome()
        if msg:
            LOG.info("Welcome message: %s", msg)

        LOG.info("Logging in as %r ...", self.ftp_user)
        self.ftp.login(user=self.ftp_user, passwd=self.ftp_password)
        self.logged_in = True

    # -------------------------------------------------------------------------
    def _run(self):
        """The underlaying startpoint of the application."""

        if not os.path.isdir(self.local_directory):
            LOG.error("Local directory %r does not exists.", self.local_directory)
            sys.exit(5)

        re_backup_dirs = re.compile(r'^\s*\d{4}[-_]+\d\d[-_]+\d\d[-_]+\d+\s*$')
        re_whitespace = re.compile(r'\s+')

        self.login_ftp()

        self.ftp.cwd(self.ftp_remote_dir)

        cur_backup_dirs = []

        dlist = self.dir_list()

        for entry in dlist:
            if self.verbose > 3:
                LOG.debug("Entry in FTP dir:\n%s", pp(entry.as_dict(short=True)))
            if re_backup_dirs.search(entry.name):
                cur_backup_dirs.append(entry.name)
            else:
                LOG.debug("FTP-Entry %r is not a valid backup directory.", entry.name)
        cur_backup_dirs.sort(key=str.lower)
        if self.verbose > 1:
            LOG.debug("Found backup directories:\n%s", pp(cur_backup_dirs))

        cur_date = datetime.utcnow()
        backup_dir_tpl = cur_date.strftime('%Y-%m-%d_%%02d')
        LOG.debug("Backup directory template: %r", backup_dir_tpl)
        cur_weekday = cur_date.timetuple().tm_wday

        # Retrieving new backup directory
        new_backup_dir = None
        i = 0
        found = False
        while not found:
            new_backup_dir = backup_dir_tpl % (i)
            if not new_backup_dir in cur_backup_dirs:
                found = True
            i += 1
        LOG.info("New backup directory: %r", new_backup_dir)
        cur_backup_dirs.append(new_backup_dir)

        type_mapping = {
            'yearly': [],
            'monthly': [],
            'weekly': [],
            'daily': [],
            'other': [],
        }

        if cur_date.month == 1 and cur_date.day == 1:
            if not new_backup_dir in type_mapping['yearly']:
                type_mapping['yearly'].append(new_backup_dir)
        if cur_date.day == 1:
            if not new_backup_dir in type_mapping['monthly']:
                type_mapping['monthly'].append(new_backup_dir)
        if cur_weekday == 6:
            # Sunday
            if not new_backup_dir in type_mapping['weekly']:
                type_mapping['weekly'].append(new_backup_dir)
        if not new_backup_dir in type_mapping['daily']:
            type_mapping['daily'].append(new_backup_dir)

        self.map_dirs2types(type_mapping, cur_backup_dirs)
        for key in type_mapping:
            type_mapping[key].sort(key=str.lower)
        if self.verbose > 2:
            LOG.debug("Mapping of found directories to backup types:\n%s", pp(type_mapping))

        for key in self.copies:
            max_copies = self.copies[key]
            cur_copies = len(type_mapping[key])
            while cur_copies > max_copies:
                type_mapping[key].pop(0)
                cur_copies = len(type_mapping[key])
        if self.verbose > 2:
            LOG.debug("Directories to keep:\n%s", pp(type_mapping))

        dirs_delete = []
        for backup_dir in cur_backup_dirs:
            keep = False
            for key in type_mapping:
                if backup_dir in type_mapping[key]:
                    if self.verbose > 2:
                        LOG.debug("Directory %r has to be kept.", backup_dir)
                    keep = True
                    continue
            if not keep:
                dirs_delete.append(backup_dir)
        LOG.debug("Directories to remove:\n%s", pp(dirs_delete))

        # Removing recursive unnecessary stuff
        for item in dirs_delete:
            self.remove_recursive(item)

        # Creating date formatted directory
        LOG.info("Creating directory %r ...", new_backup_dir)
        if not self.simulate:
            self.ftp.mkd(new_backup_dir)

        local_pattern = os.path.join(self.local_directory, '*')

        try:
            LOG.debug("Changing into %r ...", new_backup_dir)
            if not self.simulate:
                self.ftp.cwd(new_backup_dir)

            # Backing up stuff
            LOG.debug("Searching for stuff to backup in %r.", local_pattern)
            local_files = glob.glob(local_pattern)
            for local_file in sorted(local_files, key=str.lower):

                if not os.path.isfile(local_file):
                    if self.verbose > 1:
                        LOG.debug("%r is not a file, don't backup it.", local_file)
                    continue

                statinfo = os.stat(local_file)
                size = statinfo.st_size
                s = ''
                if size != 1:
                    s = 's'
                size_human = bytes2human(size, precision=1)
                remote_file = re_whitespace.sub('_', os.path.basename(local_file))
                LOG.info(
                    "Transfering file %r -> %r, size %d Byte%s (%s).",
                    local_file, remote_file, size, s, size_human)
                if not self.simulate:
                    cmd = 'STOR %s' % (remote_file)
                    with open(local_file, 'rb') as f:
                        try_nr = 0
                        while try_nr < 10:
                            try_nr += 1
                            if try_nr > 2:
                                LOG.info("Try %d transferring file %r ...", try_nr, local_file)
                            try:
                                self.ftp.storbinary(cmd, f)
                                break
                            except ftplib.error_temp as e:
                                if try_nr >= 10:
                                    msg = "Giving up trying to upload %r after %d tries: %s"
                                    LOG.error(msg, local_file, try_nr, str(e))
                                    raise
                                self.handle_error(str(e), e.__class__.__name__, False)
                                time.sleep(2)

        finally:
            LOG.debug("Changing cwd up.")
            if not self.simulate:
                self.ftp.cwd('..')

        # Detect and display current disk usages
        total_bytes = 0
        if six.PY2:
            total_bytes = long(0)

        dlist = self.dir_list()
        total_s = 'Total'
        max_len = len(total_s)

        for entry in dlist:
            if len(entry.name) > max_len:
                max_len = len(entry.name)
        max_len += 2

        LOG.info("Current disk usages:")
        for entry in dlist:

            if entry.name == '.' or entry.name == '..':
                continue

            entry_size = self.disk_usage(entry)
            total_bytes += entry_size
            s = ''
            if entry_size != 1:
                s = 's'
            b_h = bytes2human(entry_size, precision=1)
            (val, unit) = b_h.split(maxsplit=1)
            b_h_s = "%6s %s" % (val, unit)
            LOG.info("%-*r %13d Byte%s (%s)", max_len, entry.name, entry_size, s, b_h_s)

        s = ''
        if total_bytes != 1:
            s = 's'
        b_h = bytes2human(total_bytes, precision=1)
        (val, unit) = b_h.split(maxsplit=1)
        b_h_s = "%6s %s" % (val, unit)
        LOG.info("%-*s %13d Byte%s (%s)", max_len, total_s + ':', total_bytes, s, b_h_s)

    # -------------------------------------------------------------------------
    def map_dirs2types(self, type_mapping, backup_dirs):

        re_backup_date = re.compile(r'^\s*(\d+)[_\-](\d+)[_\-](\d+)')

        for backup_dir in backup_dirs:

            match = re_backup_date.search(backup_dir)
            if not match:
                if not backup_dir in type_mapping['other']:
                    type_mapping['other'].append(backup_dir)
                continue

            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))

            dt = None
            try:
                dt = datetime(year, month, day)
            except ValueError as e:
                LOG.debug("Invalid date in backup directory %r: %s", backup_dir, str(e))
                if not backup_dir in type_mapping['other']:
                    type_mapping['other'].append(backup_dir)
                continue
            weekday = dt.timetuple().tm_wday
            if dt.month == 1 and dt.day == 1:
                if not backup_dir in type_mapping['yearly']:
                    type_mapping['yearly'].append(backup_dir)
            if dt.day == 1:
                if not backup_dir in type_mapping['monthly']:
                    type_mapping['monthly'].append(backup_dir)
            if weekday == 6:
                # Sunday
                if not backup_dir in type_mapping['weekly']:
                    type_mapping['weekly'].append(backup_dir)
            if not backup_dir in type_mapping['daily']:
                type_mapping['daily'].append(backup_dir)

        if self.verbose > 3:
            LOG.debug("Mapping of found directories to backup types:\n%s", pp(type_mapping))

    # -------------------------------------------------------------------------
    def remove_recursive(self, *items):

        if not items:
            LOG.warning("Called remove_recursive() without items to remove.")
            return

        for item in items:
            LOG.info("Removing recursive %r ...", item)

            try:
                LOG.debug("Trying to change into directory %r ...", item)
                self.ftp.cwd(item)
                LOG.debug("Cwd successful.")
                dlist = self.dir_list()
                for entry in dlist:
                    if entry.name == '.' or entry.name == '..':
                        continue
                    if entry.is_dir():
                        self.remove_recursive(entry.name)
                    else:
                        LOG.info("Removing %r ...", entry.name)
                        if not self.simulate:
                            self.ftp.delete(entry.name)
                LOG.debug("Changing cwd up.")
                self.ftp.cwd('..')
                LOG.info("Removing %r ...", item)
                if not self.simulate:
                    self.ftp.rmd(item)
            except ftplib.error_perm:
                LOG.info("Object %r was not a directory, removing it.", item)
                if not self.simulate:
                    self.ftp.delete(item)
            except Exception as e:
                msg = "Cwd to %r not successful: %s" % (item, str(e))
                self.handle_error(msg, e.__class__.__name__, True)

    # -------------------------------------------------------------------------
    def dir_list(self, item_name=None):

        dlist = []

        def perform_dir_output(line):
            if self.verbose > 2:
                LOG.debug("Performing line %r ...", line)

            line = line.strip()
            if not line:
                return
            entry = DirEntry.from_dir_line(
                line, appname=self.appname, verbose=self.verbose)
            if entry:
                dlist.append(entry)

        if item_name:
            self.ftp.dir(item_name, perform_dir_output)
        else:
            self.ftp.dir(perform_dir_output)

        return dlist

    # -------------------------------------------------------------------------
    def disk_usage(self, item):
        """
        Performs a recursive determination of the disk usage of
        the given FTP directory item.
        This item must be located in the current remote directory.
        """

        if not self.logged_in:
            msg = "Could not detect disk usage of item %r, not loggen in."
            raise FTPHandlerError(msg)

        total = 0
        if six.PY2:
            total = long(0)

        if not item:
            msg = "No item to detect disk usage given."
            raise FTPHandlerError(msg)

        if self.verbose > 3:
            LOG.debug("Analyzing item:\n%s", pp(item.as_dict(short=True)))

        if not item.is_dir():
            return item.size

        if self.verbose > 2:
            msg = "Trying to detect disk usage of remote directory %r ..."
            LOG.debug(msg, item.name)

        item_dir_list = self.dir_list(item.name)
        for list_item in item_dir_list:
            if list_item.name == '.' or list_item.name == '..':
                continue
            list_item.name = item.name + '/' + list_item.name
            list_item_size = self.disk_usage(list_item)
            if self.verbose > 2:
                LOG.debug("Got disk usage of %r: %d Bytes.", list_item.name, list_item_size)
            total += list_item_size

        return total

    # -------------------------------------------------------------------------
    def post_run(self):
        """
        Dummy function to run after the main routine.
        Could be overwritten by descendant classes.

        """

        if self.ftp and self.connected:
            LOG.info("Disconnecting from %r ...", self.ftp_host)
            self.ftp.quit()

        self.ftp = None


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
