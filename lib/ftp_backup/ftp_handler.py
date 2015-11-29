#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@license: GPL3
@summary: General handler class for FTP operations
"""

# Standard modules
import logging
import os
import ftplib
import ssl
import re
import glob
from datetime import datetime

# Third party modules
import six

# Own modules
from pb_base.common import to_bool, pp, bytes2human

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import PbBaseHandler

__version__ = '0.2.0'

LOG = logging.getLogger(__name__)
DEFAULT_FTP_HOST = 'ftp'
DEFAULT_FTP_PORT = 21
DEFAULT_FTP_USER = 'anonymous'
DEFAULT_FTP_PWD = 'frank@brehm-online.com'
DEFAULT_FTP_TZ = 'UTC'
DEFAULT_FTP_TIMEOUT = 60
MAX_FTP_TIMEOUT = 3600

VERIFY_OPTS = {
    None: ssl.CERT_NONE,
    'optional': ssl.CERT_OPTIONAL,
    'required': ssl.CERT_REQUIRED,
}


# =============================================================================
class FTPHandlerError(PbBaseHandlerError):
    """
    Base exception class for all exceptions belonging to issues
    in this module
    """
    pass


# =============================================================================
class FTPHandler(PbBaseHandler):
    """
    Handler class with additional properties and methods to handle FTP operations.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, host=DEFAULT_FTP_HOST, port=DEFAULT_FTP_PORT, user=DEFAULT_FTP_USER,
            password=DEFAULT_FTP_PWD, passive=False, remote_dir=None, tls=False,
            tls_verify=None, tz=DEFAULT_FTP_TZ, timeout=DEFAULT_FTP_TIMEOUT,
            appname=None, verbose=0, version=__version__, base_dir=None,
            use_stderr=False, simulate=False, sudo=False, quiet=False,
            *targs, **kwargs):
        """Initialization of the FTPHandler object.

        @raise FTPHandlerError: on an uncoverable error.

        """

        self._host = host
        self._port = DEFAULT_FTP_PORT
        self._user = user
        self._password = password
        self._passive = bool(passive)
        self._remote_dir = remote_dir
        self._tls = bool(tls)
        self._tls_verify = None
        self._tz = ftp_tz
        self._timeout = DEFAULT_FTP_TIMEOUT

        self._connected = False
        self._logged_in = False

        self.ftp = None

        super(FTPHandler, self).__init__(
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

        self.port = port
        self.tls_verify = tls_verify
        self.timeout = timeout

    # -----------------------------------------------------------
    @property
    def host(self):
        """The FTP host to connect to."""
        return self._host

    @host.setter
    def host(self, value):
        if not value:
            self._host = DEFAULT_FTP_HOST
            return
        self._host = str(value)

    # -----------------------------------------------------------
    @property
    def port(self):
        """The listening port of the FTP host."""
        return self._port

    @port.setter
    def port(self, value):
        if not value:
            self._port = DEFAULT_FTP_PORT
            return
        p = int(value)
        if p < 1 or p >= (2 ** 16):
            msg = "Invalid port number %r for a FTP handler given." % (value)
            raise ValueError(msg)
        self._port = p

    # -----------------------------------------------------------
    @property
    def user(self):
        """The remote user on the FTP host to connect to."""
        return self._user

    @user.setter
    def user(self, value):
        if not user:
            self._user = DEFAULT_FTP_USER
            return
        self._user = str(value).strip()

    # -----------------------------------------------------------
    @property
    def password(self):
        """The password of the remote user on the FTP host to connect to."""
        return self._password

    @password.setter
    def password(self, value):
        if value is None:
            self._password = None
            return
        self._password = str(value)

    # -----------------------------------------------------------
    @property
    def remote_dir(self):
        """The directory on the FTP host to connect to."""
        return self._remote_dir

    @remote_dir.setter
    def remote_dir(self, value):
        if value is None:
            self._remote_dir = '/'
        else:
            self._remote_dir = str(value)

    # -----------------------------------------------------------
    @property
    def connected(self):
        """Flag showing, that a connection is established to a FTP server."""
        return self._connected

    # -----------------------------------------------------------
    @property
    def logged_in(self):
        """Flag showing, that the client waslogged in on the FTP server."""
        return self._logged_in

    # -----------------------------------------------------------
    @property
    def passive(self):
        """Use passive mode for data transfer."""
        return self._passive

    @passive.setter
    def passive(self, value):
        self._passive = bool(value)

    # -----------------------------------------------------------
    @property
    def tls(self):
        """Use a TLS encrypted session."""
        return self._tls

    @tls.setter
    def tls(self, value):
        val = bool(value)
        if self.connected and val != self._tls:
            msg = "Changing the property 'tls' not possible, currently connected."
            raise FTPHandlerError(msg)
        self._tls = bool(value)

    # -----------------------------------------------------------
    @property
    def tls_verify(self):
        """Defines the behaviour in TLS mode on invalid server certificates."""
        return self._tls_verify

    @tls_verify.setter
    def tls_verify(self, value):
        if value not in VERIFY_OPTS.keys():
            msg = "Invalid value %r for parameter tls_verify." % (tls_verify)
            raise ValueError(msg)
        self._tls_verify = value

    # -----------------------------------------------------------
    @property
    def timeout(self):
        """Timeout in seconds for different FTP operations."""
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        val = int(value)
        if val < 1 or val > MAX_FTP_TIMEOUT:
            msg = "Wrong timeout %d, must be between 1 and %d seconds." % (
                val, MAX_FTP_TIMEOUT)
            raise ValueError(msg)
        self._timeout = val



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
