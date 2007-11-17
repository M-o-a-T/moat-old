#!/usr/bin/python
#
# setup.py for HomEvenT

from sys import version
import os
from homevent import VERSION
from distutils.core import setup

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

script = "daemon.py"
        
setup(
    name = name,
    version = VERSION,
    description = 'Event handler for home automation',
    author = 'Matthias Urlichs',
    author_email = 'matthias@urlichs.de',
    url = 'http://homevent.smurf.noris.de',
    license = 'GPL',

	data_files=[
		('/usr/share/homevent/modules',
			[os.path.join('modules',f) for f in os.listdir('modules')
				if f.endswith('.py') and not f.startswith('.')]),
		('/etc/homevent',['daemon.he']),
	],
    modules_check = modules_check,
    packages = ['homevent'],
    scripts = [script],
    #cmdclass={'install_data' : my_install_data},
    )
