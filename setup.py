#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: LGPL3+
@copyright: © 2015 Frank Brehm, Berlin
@summary: Perform a selective backup to a FTP server
"""

import os
import sys
import re
import pprint
import datetime

# Third party modules
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# own modules:
cur_dir = os.getcwd()
if sys.argv[0] != '' and sys.argv[0] != '-c':
    cur_dir = os.path.dirname(sys.argv[0])

libdir = os.path.join(cur_dir, 'lib')
bindir = os.path.join(cur_dir, 'bin')
pkg_dir = os.path.join(libdir, 'ftp_backup')
init_py = os.path.join(pkg_dir, '__init__.py')

if os.path.isdir(libdir) and os.path.isdir(pkg_dir) and os.path.exists(init_py):
    sys.path.insert(0, os.path.abspath(libdir))

import ftp_backup

packet_version = ftp_backup.__version__

packet_name = 'ftp_backup'
debian_pkg_name = 'ftp-backup'
readme_file = 'README.md'

__author__ = 'Frank Brehm'
__contact__ = 'frank@brehm-online.com'
__copyright__ = '(C) 2015 Frank Brehm, Berlin'
__license__ = 'LGPL3+'
__desc__ = 'Perform a selective backup to a FTP server.'


# -----------------------------------
def read(fname):
    content = None
    print("Reading %r ..." % (fname))
    if sys.version_info[0] > 2:
        with open(fname, 'r', encoding='utf-8') as fh:
            content = fh.read()
    else:
        with open(fname, 'r') as fh:
            content = fh.read()
    return content


# -----------------------------------
def is_python_file(filename):
    if filename.endswith('.py'):
        return True
    else:
        return False

# -----------------------------------
debian_dir = os.path.join(cur_dir, 'debian')
changelog_file = os.path.join(debian_dir, 'changelog')
readme_file = os.path.join(cur_dir, readme_file)


# -----------------------------------
def get_debian_version():
    if not os.path.isfile(changelog_file):
        return None
    changelog = read(changelog_file)
    first_row = changelog.splitlines()[0].strip()
    if not first_row:
        return None
    pattern = r'^' + re.escape(debian_pkg_name) + r'\s+\(([^\)]+)\)'
    match = re.search(pattern, first_row)
    if not match:
        return None
    return match.group(1).strip()

debian_version = get_debian_version()
if debian_version is not None and debian_version != '':
    packet_version = debian_version


# -----------------------------------
local_version_file = os.path.join(pkg_dir, 'local_version.py')
local_version_file_content = '''\
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: %(author)s
@contact: %(contact)s
@copyright: © %(year)d by %(author)s, Berlin
@summary: %(desc)s
"""

__author__ = '%(author)s <%(contact)s>'
__copyright__ = '(C) %(year)d by %(author)s, Berlin'
__contact__ = %(author)r
__version__ = %(version)r
__license__ = %(license)r

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
'''


# -----------------------------------
def write_local_version():

    cur_year = datetime.date.today().year
    vals = {
        'author': __author__,
        'contact': __contact__,
        'desc': __desc__,
        'year': cur_year,
        'version': packet_version,
        'license': __license__,
    }
    content = local_version_file_content % vals
    # print(content)

    fh = None
    try:
        if sys.version_info[0] > 2:
            fh = open(local_version_file, 'wt', encoding='utf-8')
        else:
            fh = open(local_version_file, 'wt')
        fh.write(content)
    finally:
        if fh:
            fh.close

# Write lib/storage_tools/local_version.py
write_local_version()


# -----------------------------------
def pp(obj):
    pprinter = pprint.PrettyPrinter(indent=4)
    return pprinter.pformat(obj)


# -----------------------------------
scripts = [
    'bin/backup-per-ftp',
]


# -----------------------------------
setup(
    name=packet_name,
    version=packet_version,
    description=__desc__,
    long_description=read(readme_file),
    author=__author__,
    author_email=__contact__,
    url='https://github.com/fbrehm/ftp-backup',
    license=__license__,
    platforms=['posix'],
    package_dir={'': 'lib'},
    packages=['ftp_backup', ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    provides=[packet_name],
    scripts=scripts,
    requires=[
        'pb_logging',
        'argparse',
        'pb_base',
    ]
)

# =======================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
