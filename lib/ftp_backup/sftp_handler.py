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

from pathlib import PurePath, PurePosixPath, Path, PosixPath

# Third party modules
import paramiko

# Own modules
from pb_base.common import to_str_or_bust as to_str
from pb_base.common import to_bool, pp, bytes2human

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import PbBaseHandler

from ftp_backup import DEFAULT_LOCAL_DIRECTORY

__version__ = '0.1.0'

LOG = logging.getLogger(__name__)

DEFAULT_SSH_SERVER = 'rsync.hidrive.strato.com'
DEFAULT_SSH_PORT = 22
DEFAULT_SSH_USER = 'frank.brehm'
DEFAULT_REMOTE_DIR = PurePosixPath(
    os.sep + os.path.join('users', DEFAULT_SSH_USER, 'Backup'))
DEFAULT_SSH_TIMEOUT = 60
DEFAULT_SSH_KEY = PosixPath(os.path.expanduser('~backup/.ssh/id_rsa'))


# =============================================================================
class SFTPHandlerError(PbBaseHandlerError):
    """
    Base exception class for all exceptions belonging to issues
    in this module
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
            appname=None, verbose=0, version=__version__, base_dir=None,
            use_stderr=False, simulate=False, sudo=False, quiet=False,
            *targs, **kwargs):

        self._host = DEFAULT_SSH_SERVER
        self._port = DEFAULT_SSH_PORT
        self._user = DEFAULT_SSH_USER
        self._start_remote_dir = DEFAULT_REMOTE_DIR
        self._remote_dir = None
        self.ssh_client = None
        self.sftp_client = None
        self._key_file = key_file

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
            if isinstance(value, Path):
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
        # res['timeout'] = self.timeout

        return res

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
