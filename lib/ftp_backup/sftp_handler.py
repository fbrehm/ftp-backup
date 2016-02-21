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

from numbers import Number

from pathlib import PurePath, PurePosixPath, Path, PosixPath

# Third party modules
import paramiko

# Own modules
from pb_base.common import to_str_or_bust as to_str
from pb_base.common import to_bool, pp, bytes2human

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import PbBaseHandler

from ftp_backup import DEFAULT_LOCAL_DIRECTORY

__version__ = '0.4.1'

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

        self._local_dir = DEFAULT_LOCAL_DIRECTORY

        self._simulate = False

        self._connected = False

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

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
