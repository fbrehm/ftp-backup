#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: All modules for the FTP-backup applications
"""

import os

from pathlib import PosixPath

__author__ = 'Frank Brehm <frank@brehm-online.com>'
__copyright__ = '(C) 2010 - 2015 by Frank Brehm, Berlin'
__contact__ = 'frank@brehm-online.com'
__version__ = '0.4.1'
__license__ = 'LGPLv3+'

DEFAULT_LOCAL_DIRECTORY = PosixPath(os.sep + os.path.join('var', 'backup'))

DEFAULT_COPIES_YEARLY = 2
DEFAULT_COPIES_MONTHLY = 2
DEFAULT_COPIES_WEEKLY = 2
DEFAULT_COPIES_DAILY = 2

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
