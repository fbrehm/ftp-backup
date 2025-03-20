# -*- coding: utf-8 -*-
"""
@summary: The module for special error classes on FTP/SFTP-Backups

@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2025 by Frank Brehm, Berlin
"""
from __future__ import absolute_import

# Standard modules

# Third party modules

from fb_tools.errors import HandlerError

__version__ = '0.1.0'


# =============================================================================
class FTPHandlerError(HandlerError):
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
class SFTPHandlerError(HandlerError):
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
if __name__ == '__main__':

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
