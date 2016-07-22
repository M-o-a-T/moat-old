#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2016 by Matthias Urlichs <matthias@urlichs.de>,
##  it is licensed under the GPLv3. See the file `README.rst` for details,
##  including optimistic statements by the author.
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License (included; see the file LICENSE)
##  for more details.
##
##  This header is auto-generated and may self-destruct at any time,
##  courtesy of "make update". The original is in ‘scripts/_boilerplate.py’.
##  Thus, do not remove the next line, or insert any blank lines above.
##BP

#
# setup.py for MoaT

from sys import version
import os
from moat import VERSION

#from distutils.core import setup
from setuptools import setup

name='moat'

if version < '2.4':
    sys.exit('Error: Python-2.4 or newer is required. Current version:\n %s'
             % sys.version)

setup(
    name = name,
    version = VERSION,
    description = 'Event handler for home automation',
    long_description = '''\
MoaT is a scripted event handler, originally intended for home automation.
Needless to say, it *can* be used for other things.

MoaT features a roughly-Pythonic scripting language (with simple syntax
and event handlers instead of function calls), numerous modules for
additional I/O, logging, and easy integration into existing systems.

''',
    author = 'Matthias Urlichs',
    author_email = 'matthias@urlichs.de',
    url = 'http://moat.smurf.noris.de',
	download_url = 'http://netz.smurf.noris.de/cgi/gitweb?p=moat.git;a=snapshot;h=master',
    license = 'GPL',

	zip_safe = False, 
    packages = [str(x) for x in ('moat','moat.modules')],
	package_dir={'moat': 'moat', 'moat.modules':'modules'},
    scripts = [str(x) for x in ('scripts/daemon','scripts/moat','scripts/amqpmon')]
    #cmdclass={'install_data' : my_install_data},
    )
