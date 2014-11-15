#!/usr/bin/python
# -*- coding: utf-8 -*-

##
##  Copyright © 2007, Matthias Urlichs <matthias@urlichs.de>
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

#
# setup.py for HomEvenT

from sys import version
import os
os.environ["HOMEVENT_BUILD"] = "Y"
from homevent import VERSION

#from distutils.core import setup
from setuptools import setup

name='homevent'

if version < '2.4':
    sys.exit('Error: Python-2.4 or newer is required. Current version:\n %s'
             % sys.version)


setup(
    name = name,
    version = VERSION,
    description = 'Event handler for home automation',
    long_description = '''\
HomEvenT is a scripted event handler, originally intended for home automation.
Needless to say, it *can* be used for other things.

HomEvenT features a roughly-Pythonic scripting language (with simple syntax
and event handlers instead of function calls), numerous modules for
additional I/O, logging, and easy integration into existing systems.

''',
    author = 'Matthias Urlichs',
    author_email = 'matthias@urlichs.de',
    url = 'http://homevent.smurf.noris.de',
	download_url = 'http://netz.smurf.noris.de/cgi/gitweb?p=homevent.git;a=snapshot;h=master',
    license = 'GPL',

	zip_safe = False, 
    packages = ['homevent','homevent.modules'],
	package_dir={'homevent': 'homevent', 'homevent.modules':'modules'},
    scripts = ['scripts/daemon.py','scripts/monitor.py','scripts/list.py'],
    #cmdclass={'install_data' : my_install_data},
    )
