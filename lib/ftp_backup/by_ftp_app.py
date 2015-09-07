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
import logging

# Third party modules

# Own modules
from pb_base.app import PbApplicationError

from pb_base.cfg_app import PbCfgAppError
from pb_base.cfg_app import PbCfgApp

import ftp_backup

__version__ = '0.1.0'

LOG = logging.getLogger(__name__)


# =============================================================================
class BackupByFtpApp(PbCfgApp):
    """Application class for backing up a directory to a FTP server."""

    # -------------------------------------------------------------------------
    def __init__(self, appname=None, verbose=0):
        """Constructor."""

        super(BackupByFtpApp, self).__init__(
            appname=appname,
            verbose=verbose,
            version=ftp_backup.__version__,
            cfg_dir='ftp-backup',
            hide_default_config=True,
            need_config_file=False,
        )

        self.initialized = True

    # -------------------------------------------------------------------------
    def _run(self):
        """The underlaying startpoint of the application."""

        LOG.info("Da da da...")


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
