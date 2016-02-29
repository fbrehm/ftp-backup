#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@license: GPL3
@summary: General handler class for SFTP operations
"""

# Standard modules
import logging
import os
import errno
import stat
import re

from datetime import datetime

from numbers import Number

from collections import OrderedDict

from pathlib import PurePath, PurePosixPath, Path, PosixPath

# Third party modules
import paramiko

# Own modules
from pb_base.common import to_str_or_bust as to_str
from pb_base.common import to_bool, pp, bytes2human

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import PbBaseHandler

from ftp_backup import DEFAULT_LOCAL_DIRECTORY
from ftp_backup import DEFAULT_COPIES_YEARLY, DEFAULT_COPIES_MONTHLY
from ftp_backup import DEFAULT_COPIES_WEEKLY, DEFAULT_COPIES_DAILY

__version__ = '0.6.1'

LOG = logging.getLogger(__name__)

DEFAULT_SSH_SERVER = 'rsync.hidrive.strato.com'
DEFAULT_SSH_PORT = 22
DEFAULT_SSH_USER = 'frank.brehm'
DEFAULT_REMOTE_DIR = PurePosixPath(
    os.sep + os.path.join('users', DEFAULT_SSH_USER, 'Backup'))
DEFAULT_SSH_TIMEOUT = 60
MAX_SSH_TIMEOUT = 3600
DEFAULT_SSH_KEY = PosixPath(os.path.expanduser('~backup/.ssh/id_rsa'))


# =============================================================================
class SFTPHandlerError(PbBaseHandlerError):
    """
    Base exception class for all exceptions belonging to issues
    in this module
    """
    pass


# =============================================================================
class SFTPLocalPathError(SFTPHandlerError):
    """
    Exception class for all exceptions belonging to local paths.
    """
    pass

# =============================================================================
class SFTPSetOnConnectedError(SFTPHandlerError):

    # -------------------------------------------------------------------------
    def __init__(self, prop, val):

        self.prop = prop
        self.val = val

    # -------------------------------------------------------------------------
    def __str__(self):

        return (
            "Could not set property %(prop)r to %(val)r, because the client session "
            "is already established.") % {'prop': self.prop, 'val': self.val}


# =============================================================================
class SFTPSetOnNotConnectedError(SFTPHandlerError):

    # -------------------------------------------------------------------------
    def __init__(self, prop, val):

        self.prop = prop
        self.val = val

    # -------------------------------------------------------------------------
    def __str__(self):

        return (
            "Could not set property %(prop)r to %(val)r, because the client session "
            "is still not established.") % {'prop': self.prop, 'val': self.val}


# =============================================================================
class SFTPCwdError(SFTPHandlerError):

    # -------------------------------------------------------------------------
    def __init__(self, pathname, msg):

        self._pathname = pathname
        self._msg = msg

    # -------------------------------------------------------------------------
    def __str__(self):

        err_msg = "Error changing to remote directory %(path)r: %(msg)s"
        return err_msg % {'path': self._pathname, 'msg': self._msg}


# =============================================================================
class SFTPRemoveError(SFTPHandlerError):

    # -------------------------------------------------------------------------
    def __init__(self, pathname, msg):

        self._pathname = pathname
        self._msg = msg

    # -------------------------------------------------------------------------
    def __str__(self):

        err_msg = "Error removing %(path)r: %(msg)s"
        return err_msg % {'path': self._pathname, 'msg': self._msg}


# =============================================================================
class SFTPPutError(SFTPHandlerError):

    # -------------------------------------------------------------------------
    def __init__(self, pathname, msg):

        self._pathname = pathname
        self._msg = msg

    # -------------------------------------------------------------------------
    def __str__(self):

        err_msg = "Could not put file %(path)r: %(msg)s"
        return err_msg % {'path': self._pathname, 'msg': self._msg}


# =============================================================================
class SFTPHandler(PbBaseHandler):
    """
    Handler class with additional properties and methods to handle SFTP operations.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, host=DEFAULT_SSH_SERVER, port=DEFAULT_SSH_PORT, user=DEFAULT_SSH_USER,
            local_dir=DEFAULT_LOCAL_DIRECTORY, remote_dir=None,
            timeout=DEFAULT_SSH_TIMEOUT, key_file=DEFAULT_SSH_KEY,
            appname=None, base_dir=None, verbose=0, version=__version__,
            use_stderr=False, simulate=False, sudo=False, quiet=False,
            *targs, **kwargs):

        self._host = DEFAULT_SSH_SERVER
        self._port = DEFAULT_SSH_PORT
        self._user = DEFAULT_SSH_USER
        self._start_remote_dir = DEFAULT_REMOTE_DIR
        self._remote_dir = None
        self.ssh_client = None
        self.sftp_client = None
        self._key_file = DEFAULT_SSH_KEY
        self._timeout = DEFAULT_SSH_TIMEOUT
        self._new_backup_dir = None

        self._local_dir = DEFAULT_LOCAL_DIRECTORY

        self._simulate = False

        self._connected = False

        self.copies = {
            'yearly': DEFAULT_COPIES_YEARLY,
            'monthly': DEFAULT_COPIES_MONTHLY,
            'weekly': DEFAULT_COPIES_WEEKLY,
            'daily': DEFAULT_COPIES_DAILY,
        }

        super(SFTPHandler, self).__init__(
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            use_stderr=use_stderr,
            initialized=False,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
        )

        self.host = host
        self.port = port
        self.user = user
        self.start_remote_dir = remote_dir
        self.key_file = key_file
        self.local_dir = local_dir

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # -----------------------------------------------------------
    @property
    def connected(self):
        """Flag showing, that a connection is established to a SSH server."""
        return self._connected

    # -----------------------------------------------------------
    @property
    def host(self):
        """The SSH host to connect to."""
        return self._host

    @host.setter
    def host(self, value):
        if self.connected:
            raise SFTPSetOnConnectedError('host', value)
        if not value:
            self._host = DEFAULT_SSH_SERVER
            return
        self._host = str(value)

    # -----------------------------------------------------------
    @property
    def port(self):
        """The listening TCP port of the SSH server."""
        return self._port

    @port.setter
    def port(self, value):
        if self.connected:
            raise SFTPSetOnConnectedError('port', value)
        if not value:
            self._port = DEFAULT_SSH_PORT
            return
        p = int(value)
        if p < 1 or p >= (2 ** 16):
            msg = "Invalid port number %r for a SSH connection given." % (value)
            raise ValueError(msg)
        self._port = p

    # -----------------------------------------------------------
    @property
    def user(self):
        """The remote user on the SSH server to connect to."""
        return self._user

    @user.setter
    def user(self, value):
        if self.connected:
            raise SFTPSetOnConnectedError('user', value)
        if not value:
            self._user = DEFAULT_SSH_USER
            return
        self._user = str(value).strip()

    # -----------------------------------------------------------
    @property
    def start_remote_dir(self):
        """The directory on the SSH server to connect to on establishing
            the connection."""
        return self._start_remote_dir

    @start_remote_dir.setter
    def start_remote_dir(self, value):
        if self.connected:
            raise SFTPSetOnConnectedError('start_remote_dir', value)
        if value is None:
            self._start_remote_dir = PurePosixPath('/')
        else:
            if isinstance(value, PurePath):
                self._start_remote_dir = value
            else:
                self._start_remote_dir = PurePosixPath(str(value))

    # -----------------------------------------------------------
    @property
    def remote_dir(self):
        """The remote directory during an established SFTP connection."""
        return self._remote_dir

    @remote_dir.setter
    def remote_dir(self, value):
        if not self.connected:
            raise SFTPSetOnNotConnectedError('remote_dir', value)

        if value is None:
            self.sftp_client.chdir(str(self.start_remote_dir))
        else:
            self.sftp_client.chdir(str(value))
        self._remote_dir = PurePosixPath(self.sftp_client.getcwd())

    # -----------------------------------------------------------
    @property
    def local_dir(self):
        """The local directory, from where to backup the files."""
        return self._local_dir

    @local_dir.setter
    def local_dir(self, value):

        if value is None:
            raise ValueError("The local directory may not be set to None.")

        ldir = None
        if isinstance(value, Path):
            ldir = value
        else:
            ldir = PosixPath(str(value))

        if str(ldir).startswith('~'):
            ldir = ldir.__class__(os.path.expanduser(str(ldir)))

        if self.connected:
            if not ldir.is_dir():
                msg = "Directory %r does not exists or is not a directory." % (ldir)
                raise SFTPLocalPathError(msg)
            os.chdir(str(ldir))

        self.base_dir = str(ldir)
        self._local_dir = ldir

    # -----------------------------------------------------------
    @property
    def key_file(self):
        """The private SSH key file for establishing the SSH connection."""
        return self._key_file

    @key_file.setter
    def key_file(self, value):
        if self.connected:
            raise SFTPSetOnConnectedError('key_file', value)
        kfile = None
        if value is None:
            kfile = DEFAULT_SSH_KEY
        else:
            if isinstance(value, Path):
                kfile = value
            else:
                kfile = PosixPath(str(value))

        if str(kfile).startswith('~'):
            kfile = kfile.expanduser()

        self._key_file = kfile

    # -----------------------------------------------------------
    @property
    def timeout(self):
        """The listening TCP port of the SSH server."""
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        if not isinstance(value, Number):
            raise TypeError("The timeout must be a number, not %r." % (value))
        if value < 1 or value >= MAX_SSH_TIMEOUT:
            msg = "Invalid timeout %r given." % (value)
            raise ValueError(msg)
        self._timeout = value

    # -----------------------------------------------------------
    @property
    def new_backup_dir(self):
        """The new backup directory."""
        return self._new_backup_dir

    @new_backup_dir.setter
    def new_backup_dir(self, value):
        if value is None:
            self._new_backup_dir = None
            return
        if isinstance(value, PurePosixPath):
            self._new_backup_dir = value
            return
        self._new_backup_dir = PurePosixPath(str(value))

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(SFTPHandler, self).as_dict(short=short)
        res['host'] = self.host
        res['port'] = self.port
        res['user'] = self.user
        res['start_remote_dir'] = self.start_remote_dir
        res['remote_dir'] = self.remote_dir
        res['connected'] = self.connected
        res['key_file'] = self.key_file
        res['local_dir'] = self.local_dir
        res['timeout'] = self.timeout
        res['new_backup_dir'] = self.new_backup_dir

        return res

    # -------------------------------------------------------------------------
    def __del__(self):

        if self.connected:
            self.disconnect()

    # -------------------------------------------------------------------------
    def _check_local_paths(self):

        LOG.debug("Checking all local paths ...")

        #---------
        if self.verbose > 1:
            LOG.debug("Checking SSH key file %r ...", str(self.key_file))

        if not self.key_file.exists():
            msg = "SSH key file %r does not exists." % (str(self.key_file))
            raise SFTPHandlerError(msg)

        if not self.key_file.is_file():
            msg = "SSH key file %r is not a regular file." % (str(self.key_file))
            raise SFTPHandlerError(msg)

        if not os.access(str(self.key_file), os.R_OK):
            msg = "No read access to %r." % (str(self.key_file))
            raise SFTPHandlerError(msg)

        #---------
        if self.verbose > 1:
            LOG.debug("Checking local backup directory %r ...", str(self.local_dir))

        if not self.local_dir.is_dir():
            msg = "Directory %r does not exists or is not a directory." % (self.local_dir)
            raise SFTPLocalPathError(msg)
        os.chdir(str(self.local_dir))

    # -------------------------------------------------------------------------
    def connect(self):

        if self.connected:
            LOG.warning("The SFTP client is already connected.")
            return

        self._check_local_paths()

        LOG.info("SSH connect to %s@%s ...", self.user, self.host)
        self.ssh_client.connect(
            self.host, port=self.port, username=self.user, key_filename=str(self.key_file),
            timeout=self.timeout)
        self._connected = True

        self.sftp_client = self.ssh_client.open_sftp()

        self.sftp_client.chdir(str(self.start_remote_dir))
        self._remote_dir = PurePosixPath(self.sftp_client.getcwd())

    # -------------------------------------------------------------------------
    def disconnect(self):

        if not self.connected:
            LOG.warning("The SFTP client is already disconnected.")
            return

        LOG.info("Disconnecting from %s ...", self.host)
        self.sftp_client = None
        self.ssh_client.close()
        self._connected = False

    # -------------------------------------------------------------------------
    def exists(self, remote_file):

        rfile = str(remote_file)
        if not self.connected:
            raise SFTPHandlerError("Cannot check existence of %r, not connected." % (rfile))

        try:
            self.sftp_client.stat(rfile)
        except FileNotFoundError:
            return False
        return True

    # -------------------------------------------------------------------------
    def mkdir(self, path, mode=None):

        if mode is None:
            mode = 0o755
        path = str(path)
        if not self.connected:
            raise SFTPHandlerError("Cannot create remote %r, not connected." % (rpath))

        LOG.info("Creating remote directory %r with mode %04o ...", path, mode)
        self.sftp_client.mkdir(path, mode)

    # -------------------------------------------------------------------------
    def is_dir(self, remote_path):

        rpath = str(remote_path)
        if not self.connected:
            raise SFTPHandlerError("Cannot check stat of %r, not connected." % (rpath))

        try:
            fstat = self.sftp_client.stat(rpath)
        except FileNotFoundError:
            return False

        if self.verbose > 2:
            LOG.debug("Got a state of %r: %r", rpath, fstat)
        mode = fstat.st_mode
        if self.verbose > 1:
            LOG.debug("Mode of %r: %04o", rpath, stat.S_IMODE(mode))

        if stat.S_ISDIR(mode):
            return True
        return False

    # -------------------------------------------------------------------------
    def dir_list(self, path='.'):

        path = str(path)

        if not self.connected:
            raise SFTPHandlerError("Cannot get directory list of %r, not connected." % (path))
        LOG.debug("Getting directory list of %r ...", path)

        dlist = OrderedDict()
        for entry in self.sftp_client.listdir(path):
            dlist[entry] = {}

        for entry in dlist:
            entry_path = os.path.join(path, entry)
            entry_stat = self.sftp_client.stat(entry_path)
            if self.verbose > 2:
                LOG.debug("Got stat of %r: %r.", entry_path, entry_stat)
            dlist[entry] = entry_stat

        return dlist

    # -------------------------------------------------------------------------
    def cleanup_old_backupdirs(self):

        LOG.info("Cleaning up old backup directories ...")
        re_backup_dirs = re.compile(r'^\s*\d{4}[-_]+\d\d[-_]+\d\d[-_]+\d+\s*$')

        cur_backup_dirs = []
        dlist = self.dir_list()
        for entry in dlist:
            entry_stat = dlist[entry]
            if self.verbose > 2:
                LOG.debug("Checking entry %r ...", pp(entry))
            if not stat.S_ISDIR(entry_stat.st_mode):
                if self.verbose > 2:
                    LOG.debug("%r is not a directory.", entry)
                continue
            if re_backup_dirs.search(entry):
                cur_backup_dirs.append(entry)
        cur_backup_dirs.sort(key=str.lower)

        if self.verbose > 1:
            LOG.debug("Found backup directories to check:\n%s", pp(cur_backup_dirs))

        cur_date = datetime.utcnow()
        cur_weekday = cur_date.timetuple().tm_wday

        # Retrieving new backup directory
        self._get_new_backup_dir(cur_backup_dirs)
        new_backup_dir = str(self.new_backup_dir)
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

        self._map_dirs2types(type_mapping, cur_backup_dirs)
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

        if dirs_delete:
            self.remove_recursive(*dirs_delete)

    # -------------------------------------------------------------------------
    def _get_new_backup_dir(self, cur_backup_dirs=None):
        # Retrieving new backup directory

        if cur_backup_dirs is None:
            cur_backup_dirs = []
            dlist = self.dir_list()
            for entry in dlist:
                entry_stat = dlist[entry]
                if self.verbose > 2:
                    LOG.debug("Checking entry %r ...", pp(entry))
                if not stat.S_ISDIR(entry_stat.st_mode):
                    if self.verbose > 2:
                        LOG.debug("%r is not a directory.", entry)
                    continue
                cur_backup_dirs.append(entry)

        cur_date = datetime.utcnow()
        backup_dir_tpl = cur_date.strftime('%Y-%m-%d_%%02d')
        LOG.debug("Backup directory template: %r", backup_dir_tpl)

        new_backup_dir = None
        i = 0
        found = False
        while not found:
            new_backup_dir = backup_dir_tpl % (i)
            if not new_backup_dir in cur_backup_dirs:
                found = True
            i += 1
        self.new_backup_dir = new_backup_dir
        LOG.info("New backup directory: %r", str(self.new_backup_dir))

    # -------------------------------------------------------------------------
    def _map_dirs2types(self, type_mapping, backup_dirs):

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

        if not self.connected:
            raise SFTPHandlerError("Cannot remove %r, not connected." % (items))

        for item in items:

            ipath = item
            if not isinstance(item, PurePosixPath):
                ipath = PurePosixPath(str(item))
            if str(ipath) == '.' or str(ipath) == '..':
                LOG.warning("Cannot remove special directory %r.", str(ipath))
                continue

            if self.is_dir(ipath):
                LOG.info("Removing recursive %r ...", str(ipath))
                dlist = self.sftp_client.listdir(str(ipath))
                for entry in dlist:
                    entry_path = PurePosixPath(os.path.join(str(ipath), entry))
                    self.remove_recursive(entry_path)
                LOG.info("Removing directory %r ...", str(ipath))
                if not self.simulate:
                    self.sftp_client.rmdir(str(ipath))
                continue

            LOG.info("Removing file %r ...", str(ipath))
            if not self.simulate:
                self.sftp_client.remove(str(ipath))

    # -------------------------------------------------------------------------
    def do_backup(self):

        if not self.new_backup_dir:
            self._get_new_backup_dir(cur_backup_dirs)
        new_backup_dir = str(self.new_backup_dir)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
