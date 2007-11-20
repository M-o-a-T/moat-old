#!/usr/bin/python
#
# setup.py for HomEvenT

from sys import version
import os
from homevent import VERSION

#from distutils.core import setup
from setuptools import setup

name='homevent'

if version < '2.4':
    sys.exit('Error: Python-2.4 or newer is required. Current version:\n %s'
             % sys.version)


def modules_check():
    '''Check if necessary modules is installed.
    The function is executed by distutils (by the install command).'''
    try:
        import twisted
    except ImportError:
        sys.exit('Error: the Twisted framework is required.')
        raise

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

It is based on Twisted.
''',
    author = 'Matthias Urlichs',
    author_email = 'matthias@urlichs.de',
    url = 'http://homevent.smurf.noris.de',
	download_url = 'http://netz.smurf.noris.de/cgi/gitweb?p=homevent.git;a=snapshot;h=master',
    license = 'GPL',

	zip_safe = False, 
    modules_check = modules_check,
    packages = ['homevent','homevent.modules'],
	package_dir={'homevent': 'homevent', 'homevent.modules':'modules'},
    scripts = ['scripts/daemon.py'],
    #cmdclass={'install_data' : my_install_data},
    )
