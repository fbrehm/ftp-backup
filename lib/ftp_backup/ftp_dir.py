#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@license: GPL3
@summary: Module for classes for listings of FTP directories
"""

# Standard modules
import logging
import re
from datetime import datetime

# Third party modules
import six

# Own modules

from pb_base.common import to_bool, pp
from pb_base.common import to_str_or_bust as to_str

from pb_base.object import PbBaseObjectError
from pb_base.object import PbBaseObject

__version__ = '0.1.0'

LOG = logging.getLogger(__name__)

# Permission Constants

# User permissions
STAT_RUSR = 0o1
STAT_WUSR = 0o2
STAT_XUSR = 0o4

# Group permisions
STAT_RGRP = 0o10
STAT_WGRP = 0o20
STAT_XGRP = 0o40

# Permissions for others
STAT_ROTH = 0o100
STAT_WOTH = 0o200
STAT_XOTH = 0o400

# Is a directory
STAT_ISDIR = 0o1000

# =============================================================================
class EntryPermissions(object):

    pat_triple = r'([-r])([-w])([-x])'
    pat_from_str = r'^\s*([-d])' + pat_triple + pat_triple + pat_triple + r'\s*$'
    re_from_str = re.compile(pat_from_str, re.IGNORECASE)
    re_dec = re.compile(r'^\s*(\d+)\s*$')
    re_oct = re.compile(r'^\s*0?o([0-7]+)\s*$', re.IGNORECASE)
    re_hex = re.compile(r'^\s*0?x([0-9a-f]+)\s*$', re.IGNORECASE)

    # -------------------------------------------------------------------------
    def __init__(self, permission):

        self._permission = 0
        self.set_permission(permission)

    # -----------------------------------------------------------
    @property
    def permission(self):
        return self._permission

    @permission.setter
    def permission(self, permission):
        self.set_permission(permission)

    # -------------------------------------------------------------------------
    def set_permission(self, permission):

        if isinstance(permission, int):
            if permission < 0:
                msg = "Invalid permission %d." % (permission)
                raise ValueError(msg)
            self._permission = permission
        elif isinstance(permission, six.string_types) or isinstance(permission, six.binary_type):
            self._permission = self.to_int(permission)
        else:
            msg = "Invalid permission %r." % (permission)
            raise ValueError(msg)

        self._permission &= 0o1777
    # -------------------------------------------------------------------------
    @classmethod
    def to_int(cls, permission):

        perm = 0
        v = to_str(permission)
        match = cls.re_from_str.search(v)
        if match:
            if match.group(1) != '-':
                perm | STAT_ISDIR
            if match.group(2) != '-':
                perm | STAT_RUSR
            if match.group(3) != '-':
                perm | STAT_WUSR
            if match.group(4) != '-':
                perm | STAT_XUSR
            if match.group(5) != '-':
                perm | STAT_RGRP
            if match.group(6) != '-':
                perm | STAT_WGRP
            if match.group(7) != '-':
                perm | STAT_XGRP
            if match.group(8) != '-':
                perm | STAT_ROTH
            if match.group(9) != '-':
                perm | STAT_WOTH
            if match.group(10) != '-':
                perm | STAT_XOTH
            return perm

        match = cls.re_dec.search(v)
        if match:
            perm = int(match.group(1))
            return perm
        
        match = cls.re_oct.search(v)
        if match:
            perm = int(match.group(1), 8)
            return perm
        
        match = cls.re_hex.search(v)
        if match:
            perm = int(match.group(1), 16)
            return perm

        msg = "Invalid permission %r." % (permission)
        raise ValueError(msg)

    # -------------------------------------------------------------------------
    def __repr__(self):
        out = "<%s(permission=%r)>" % (self.__class__.__name__,  self.permission)
        return out

    # -------------------------------------------------------------------------
    def __str__(self):

        out = ''

        if self.permission & STAT_ISDIR:
            out += 'd'
        else:
            out += '-'

        if self.permission & STAT_RUSR:
            out += 'r'
        else:
            out += '-'

        if self.permission & STAT_WUSR:
            out += 'w'
        else:
            out += '-'

        if self.permission & STAT_XUSR:
            out += 'x'
        else:
            out += '-'

        if self.permission & STAT_RGRP:
            out += 'r'
        else:
            out += '-'

        if self.permission & STAT_WGRP:
            out += 'w'
        else:
            out += '-'

        if self.permission & STAT_XGRP:
            out += 'x'
        else:
            out += '-'

        if self.permission & STAT_ROTH:
            out += 'r'
        else:
            out += '-'

        if self.permission & STAT_WOTH:
            out += 'w'
        else:
            out += '-'

        if self.permission & STAT_XOTH:
            out += 'x'
        else:
            out += '-'

        return out

    # -------------------------------------------------------------------------
    def is_dir(self):
        if self.permission & STAT_ISDIR:
            return True
        else:
            return False

    # -------------------------------------------------------------------------
    def is_file(self):
        if self.permission & STAT_ISDIR:
            return False
        else:
            return True

    # -------------------------------------------------------------------------
    def access(self, mode):
        if self.permission & mode:
            return True
        return False

    # -------------------------------------------------------------------------
    def user_has_read_access(self):
        return self.access(STAT_RUSR)

    # -------------------------------------------------------------------------
    def user_has_write_access(self):
        return self.access(STAT_WUSR)

    # -------------------------------------------------------------------------
    def user_has_exec_access(self):
        return self.access(STAT_XUSR)

    # -------------------------------------------------------------------------
    def group_has_read_access(self):
        return self.access(STAT_RGRP)

    # -------------------------------------------------------------------------
    def group_has_write_access(self):
        return self.access(STAT_WGRP)

    # -------------------------------------------------------------------------
    def group_has_exec_access(self):
        return self.access(STAT_XGRP)

    # -------------------------------------------------------------------------
    def other_has_read_access(self):
        return self.access(STAT_ROTH)

    # -------------------------------------------------------------------------
    def other_has_write_access(self):
        return self.access(STAT_WOTH)

    # -------------------------------------------------------------------------
    def other_has_exec_access(self):
        return self.access(STAT_XOTH)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
