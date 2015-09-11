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

__version__ = '0.2.2'

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
        self._set_permission(permission)

    # -----------------------------------------------------------
    @property
    def permission(self):
        return self._permission

    @permission.setter
    def permission(self, permission):
        self._set_permission(permission)

    # -------------------------------------------------------------------------
    def _set_permission(self, permission):

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
    def oct(self):
        return "0o%04o" % (self.permission)

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


# =============================================================================
class DirEntry(PbBaseObject):

    # drwx---r-x   2 b082473  cust         8192 Jan  1  2014 2014-01-01_00
    # drwx---r-x   2 b082473  cust         8192 May  1 08:20 2015-05-01_00
    pat_dir_line = r'^(\S{10})\s+(\d+)\s+(\S+)\s+(\S+)\s+(\d+)\s+'
    pat_dir_line += r'(\S+\s+\S+\s+\S+)\s+(.*)'
    re_dir_line = re.compile(pat_dir_line)

    def __init__(
        self, name=None, perms=None, num_hardlinks=None, user=None, group=None,
            size=None, mtime=None, appname=None, verbose=0, initialized=False):

        self._name = None 
        self._perms = EntryPermissions(0)
        self._num_hardlinks = None
        self._user = None
        self._group = None
        self._size = 0
        self._mtime = None

        super(DirEntry, self).__init__(
            appname=appname,
            verbose=verbose,
            version=__version__,
            initialized=False,
        )

        if name is not None:
            self.name = name

        if perms is not None:
            self.perms = perms

        if num_hardlinks is not None:
            self.num_hardlinks = num_hardlinks

        if user is not None:
            self.user = user

        if group is not None:
            self.group = group

        if size is not None:
            self.size = size

        if mtime is not None:
            self.mtime = mtime

        self.initialized = initialized

    # -----------------------------------------------------------
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        if isinstance(val, six.string_types) or isinstance(val, six.binary_type):
            self._name = to_str(val)
        else:
            msg = "Invalid FTP entry name %r." % (val)
            raise ValueError(msg)

    # -----------------------------------------------------------
    @property
    def perms(self):
        return self._perms

    @perms.setter
    def perms(self, val):
        self._perms = EntryPermissions(val)

    # -----------------------------------------------------------
    @property
    def num_hardlinks(self):
        return self._num_hardlinks

    @num_hardlinks.setter
    def num_hardlinks(self, val):
        v = int(val)
        if v < 0:
            msg = "Invalid number of hardlinks %r." % (val)
            raise ValueError(msg)
        self._num_hardlinks = v

    # -----------------------------------------------------------
    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, val):
        if isinstance(val, six.string_types) or isinstance(val, six.binary_type):
            self._user = to_str(val)
        else:
            msg = "Invalid FTP user name %r." % (val)
            raise ValueError(msg)

    # -----------------------------------------------------------
    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, val):
        if isinstance(val, six.string_types) or isinstance(val, six.binary_type):
            self._group = to_str(val)
        else:
            msg = "Invalid FTP group name %r." % (val)
            raise ValueError(msg)

    # -----------------------------------------------------------
    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, val):
        v = int(val)
        if v < 0:
            msg = "Invalid size of the FTP entry %r." % (val)
            raise ValueError(msg)
        self._size = v

    # -----------------------------------------------------------
    @property
    def mtime(self):
        return self._mtime

    @mtime.setter
    def mtime(self, val):
        if isinstance(val, datetime):
            self._mtime = val
        elif isinstance(val, six.string_types) or isinstance(val, six.binary_type):
            v = to_str(val)
            pat_older = '%b %d %Y'
            pat_newer = '%b %d %H:%M'
            cur_year = datetime.utcnow().year
            try:
                self._mtime = datetime.strptime(v, pat_older)
            except ValueError:
                try:
                    mt = datetime.strptime(v, pat_newer)
                    self._mtime = datetime(cur_year, mt.month, mt.day, mt.hour, mt.minute)
                except ValueError:
                    msg = "Invalid mtime of the FTP entry %r." % (val)
                    raise ValueError(msg)
        else:
            msg = "Invalid mtime of the FTP entry %r." % (val)
            raise ValueError(msg)

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(DirEntry, self).as_dict(short=short)
        res['name'] = self.name
        res['perms'] = self.perms.oct()
        res['num_hardlinks'] = self.num_hardlinks
        res['user'] = self.user
        res['group'] = self.group
        res['size'] = self.size
        res['mtime'] = self.mtime

        return res

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("perms=%r" % (self.perms.oct()))
        fields.append("num_hardlinks=%r" % (self.num_hardlinks))
        fields.append("user=%r" % (self.user))
        fields.append("group=%r" % (self.group))
        fields.append("size=%r" % (self.size))
        fields.append("mtime=%r" % (self.mtime))
        fields.append("name=%r" % (self.name))
        fields.append("appname=%r" % (self.appname))
        fields.append("verbose=%r" % (self.verbose))
        fields.append("initialized=%r" % (self.initialized))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def __str__(self):

        tpl = '%(perm)s %(hl)3d %(user)-8s %(group)-8s %(size)12d '
        tpl += '%(mtime)s %(name)s'
        out = {
            'perm': str(self.perms),
            'hl': 0,
            'user': 'None',
            'group': 'None',
            'size': 0,
            'mtime': 'None',
            'name': 'None',
        }
        if self.name is not None:
            out['name'] = self.name
        if self.num_hardlinks is not None:
            out['hl'] = self.num_hardlinks
        if self.user is not None:
            out['user'] = self.user
        if self.group is not None:
            out['group'] = self.group
        if self.size is not None:
            out['size'] = self.size
        if self.mtime is not None:
            out['mtime'] = self.mtime.strftime('%Y-%m-%d %H:%M')

        return tpl % out

    # -------------------------------------------------------------------------
    @classmethod
    def from_dir_line(cls, line, appname=None, verbose=0):

        line = line.strip()
        match = cls.re_dir_line.search(line)
        if not match:
            LOG.warn("Invalid line in FTP dir output %r.", line)
            return None

        dir_entry = cls(appname=appname, verbose=verbose)

        dir_entry.perms = match.group(1)
        dir_entry.num_hardlinks = match.group(2)
        dir_entry.user = match.group(3)
        dir_entry.group = match.group(4)
        dir_entry.size = match.group(5)
        dir_entry.mtime = match.group(6)
        dir_entry.name = match.group(7)
        dir_entry.initialized = True

        if verbose > 3:
            LOG.debug('Initialized FTP dir entry:\n%s', pp(dir_entry.as_dict(short=True)))

        return dir_entry

    # -------------------------------------------------------------------------
    def __cmp__(self, other):
        """Helper method, which is used by sorted()."""

        if not isinstance(other, DirEntry):
            msg = "Trying to compare apples (%s) with pears (%s)." % (
                self.__class__.__name__, other.__class__.__name__)
            raise TypeError(msg)

        return cmp(self.name.lower(), self.other.lower())

    # -------------------------------------------------------------------------
    def is_dir(self):
        return self.perms.is_dir()

    # -------------------------------------------------------------------------
    def is_file(self):
        return self.perms.is_file()


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
