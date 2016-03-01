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
import time
from datetime import datetime

# Third party modules
import six

# Own modules
from pb_base.common import to_bool, pp, bytes2human

from pb_base.handler import PbBaseHandlerError
from pb_base.handler import PbBaseHandler

from ftp_backup.ftp_dir import DirEntry

__version__ = '0.4.2'

LOG = logging.getLogger(__name__)
DEFAULT_FTP_HOST = 'ftp'
DEFAULT_FTP_PORT = 21
DEFAULT_FTP_USER = 'anonymous'
DEFAULT_FTP_PWD = 'frank@brehm-online.com'
DEFAULT_FTP_TZ = 'UTC'
DEFAULT_FTP_TIMEOUT = 60
DEFAULT_MAX_STOR_ATTEMPTS = 10
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
class FTPCwdError(FTPHandlerError):

    # -------------------------------------------------------------------------
    def __init__(self, pathname, msg):

        self._pathname = pathname
        self._msg = msg

    # -------------------------------------------------------------------------
    def __str__(self):

        err_msg = "Error changing to remote directory %(path)r: %(msg)s"
        return err_msg % {'path': self._pathname, 'msg': self._msg}


# =============================================================================
class FTPRemoveError(FTPHandlerError):

    # -------------------------------------------------------------------------
    def __init__(self, pathname, msg):

        self._pathname = pathname
        self._msg = msg

    # -------------------------------------------------------------------------
    def __str__(self):

        err_msg = "Error removing %(path)r: %(msg)s"
        return err_msg % {'path': self._pathname, 'msg': self._msg}


# =============================================================================
class FTPPutError(FTPHandlerError):

    # -------------------------------------------------------------------------
    def __init__(self, pathname, msg):

        self._pathname = pathname
        self._msg = msg

    # -------------------------------------------------------------------------
    def __str__(self):

        err_msg = "Could not transfer file %(path)r: %(msg)s"
        return err_msg % {'path': self._pathname, 'msg': self._msg}


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
            max_stor_attempts=DEFAULT_MAX_STOR_ATTEMPTS,
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
        self._remote_dir = '/'
        self._tls = bool(tls)
        self._tls_verify = None
        self._tz = tz
        self._timeout = DEFAULT_FTP_TIMEOUT
        self._max_stor_attempts = DEFAULT_MAX_STOR_ATTEMPTS

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

        self.remote_dir = remote_dir
        self.port = port
        self.tls_verify = tls_verify
        self.timeout = timeout
        self.max_stor_attempts = max_stor_attempts

        self.init_ftp()

        self.initialized = True

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
    def tz(self):
        """The timezone of all operations."""
        return self._tz

    @tz.setter
    def tz(self, value):
        if value is None:
            self._tz = None
        else:
            self._tz = str(value)

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
        old_passive = self._passive
        self._passive = bool(value)
        if self.ftp and (old_passive != self._passive):
            LOG.debug("Set FTP passive mode to %r.", self._passive)
            self.ftp.set_pasv(self._passive)

    # -----------------------------------------------------------
    @property
    def tls(self):
        """Use a TLS encrypted session."""
        return self._tls

    @tls.setter
    def tls(self, value):
        val = bool(value)
        if self.connected:
            if val != self._tls:
                msg = "Changing the property 'tls' not possible, currently connected."
                raise FTPHandlerError(msg)
            self._tls = val
            self.init_ftp()
        else:
            self._tls = val

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
        if self.connected:
            if value != self._tls_verify:
                msg = "Changing the property 'tls_verify' not possible, currently connected."
                raise FTPHandlerError(msg)
            self._tls_verify = value
            self.init_ftp()
        else:
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

    # -----------------------------------------------------------
    @property
    def max_stor_attempts(self):
        """The listening port of the FTP host."""
        return self._max_stor_attempts

    @max_stor_attempts.setter
    def max_stor_attempts(self, value):
        if not value:
            self._max_stor_attempts = DEFAULT_MAX_STOR_ATTEMPTS
            return
        p = int(value)
        if p < 1:
            msg = "Invalid number %r for maximoum stor attempts." % (value)
            raise ValueError(msg)
        self._max_stor_attempts = p

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(FTPHandler, self).as_dict(short=short)
        res['host'] = self.host
        res['port'] = self.port
        res['user'] = self.user
        res['password'] = self.password
        res['remote_dir'] = self.remote_dir
        res['tz'] = self.tz
        res['connected'] = self.connected
        res['logged_in'] = self.logged_in
        res['passive'] = self.passive
        res['tls'] = self.tls
        res['tls_verify'] = self.tls_verify
        res['timeout'] = self.timeout
        res['max_stor_attempts'] = self.max_stor_attempts

        return res

    # -------------------------------------------------------------------------
    def __del__(self):

        if self.ftp and self.connected:
            self.ftp.quit()

        self.ftp = None

    # -------------------------------------------------------------------------
    def init_ftp(self):

        if self.tls:
            LOG.debug("Initializing FTP_TLS object ...")
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = VERIFY_OPTS[self.tls_verify]
            self.ftp = ftplib.FTP_TLS(context=context, timeout=self.timeout)
        else:
            LOG.debug("Initializing FTP object ...")
            self.ftp = ftplib.FTP(timeout=self.timeout)

        if self.verbose > 1:
            if self.verbose > 2:
                self.ftp.set_debuglevel(2)
            else:
                self.ftp.set_debuglevel(1)

        LOG.debug("Set FTP passive mode to %r.", self.passive)
        if self.passive:
            self.ftp.set_pasv(True)
        else:
            self.ftp.set_pasv(False)

    # -------------------------------------------------------------------------
    def login_ftp(self):

        LOG.info("Connecting to FTP server %r (port %d) ...", self.host, self.port)
        self.ftp.connect(host=self.host, port=self.port)
        self._connected = True

        msg = self.ftp.getwelcome()
        if msg:
            LOG.info("Welcome message: %s", msg)

        LOG.info("Logging in as %r ...", self.user)
        self.ftp.login(user=self.user, passwd=self.password)
        self._logged_in = True
        self.cwd(self.remote_dir)

    # -------------------------------------------------------------------------
    def cwd(self, pathname):
        """Wrapper for ftplib.FTP.cwd()."""

        new_dir = pathname
        if not os.path.isabs(pathname):
            new_dir = os.path.normpath(os.path.join(self.remote_dir, new_dir))
        if self.ftp:
            try:
                LOG.info("Changing FTP directory to %r ...", pathname)
                self.ftp.cwd(pathname)
                new_dir = self.ftp.pwd()
                LOG.debug("New FTP directory is now %r.", new_dir)
            except ftplib.error_perm as e:
                raise FTPCwdError(pathname, str(e))
        self._remote_dir = new_dir

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
    def remove(self, recursive=False, *items):

        if not items:
            self.handle_error("Called remove() without items to remove.", do_traceback=True)
            return

        for item in items:

            if not self.ftp or not self.logged_in:
                msg = "Not connected or logged in."
                raise FTPRemoveError(item, msg)

            # Remove non-recursive ...
            if not recursive:
                LOG.info("Removing %r ...", item)
                pathname_abs = os.path.join(self.remote_dir, item)
                try:
                    if not self.simulate:
                        self.ftp.delete(item)
                except ftplib.error_perm as e:
                    raise FTPRemoveError(pathname_abs, str(e))
                continue

            # The recursive approach
            LOG.info("Removing recursive %r ...", item)
            try:
                self.cwd(item)
                dlist = self.dir_list()
                for entry in dlist:
                    if entry.name == '.' or entry.name == '..':
                        continue
                    if entry.is_dir():
                        self.remove(entry.name, recursive=True)
                    else:
                        self.remove(entry.name)
                self.cwd('..')
                LOG.info("Removing directory %r ...", item)
                if not self.simulate:
                    self.ftp.rmd(item)
            except ftplib.error_perm:
                self.remove(item)
            except Exception as e:
                self.handle_error(str(e), e.__class__.__name__, True)

    # -------------------------------------------------------------------------
    def mkdirs(self, *dirs):

        if not dirs:
            self.handle_error("Called mkdirs() without directories to create.", do_traceback=True)
            return

        for directory in dirs:
            self.mkdir(directory)

    # -------------------------------------------------------------------------
    def mkdir(self, directory):

        if not self.ftp or not self.logged_in:
            msg = "Cannot create %r, not connected or logged in." % (directory)
            raise FTPHandlerError(msg)

        LOG.info("Creating directory %r ...", directory)
        if not self.simulate:
            self.ftp.mkd(new_backup_dir)

    # -------------------------------------------------------------------------
    def put_file(self, local_file, remote_file=None):

        if not self.ftp or not self.logged_in:
            msg = "Cannot put file %r, not connected or logged in." % (local_file)
            raise FTPHandlerError(msg)

        if not remote_file:
            remote_file = os.path.basename(local_file)

        if not os.path.isfile(local_file):
            raise FTPPutError(local_file, "not a regular file.")

        statinfo = os.stat(local_file)
        size = statinfo.st_size
        s = ''
        if size != 1:
            s = 's'
        size_human = bytes2human(size, precision=1)
        LOG.info(
            "Transfering file %r -> %r, size %d Byte%s (%s).",
            local_file, remote_file, size, s, size_human)
        if not self.simulate:
            cmd = 'STOR %s' % (remote_file)
            with open(local_file, 'rb') as fh:
                try_nr = 0
                while try_nr < self.max_stor_attempts:
                    try_nr += 1
                    if try_nr >= 2:
                        LOG.info("Try %d transferring file %r ...", try_nr, local_file)
                    try:
                        self.ftp.storbinary(cmd, fh)
                        break
                    except ftplib.error_temp as e:
                        if try_nr >= 10:
                            msg = "Giving up trying to upload %r after %d tries: %s"
                            LOG.error(msg, local_file, try_nr, str(e))
                            raise
                        self.handle_error(str(e), e.__class__.__name__, False)
                        time.sleep(2)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
