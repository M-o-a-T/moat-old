# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division, unicode_literals
##
##  This file is part of MoaT, the Master of all Things.
##
##  MoaT is Copyright © 2007-2015 by Matthias Urlichs <matthias@urlichs.de>,
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

"""\
This is the core of the event dispatcher.
"""

import os

VERSION = "0.7"

TESTING = "MOAT_TEST" in os.environ

	# This test is also in moat/twist.py, for recursive-import reasons

def patch():
	"""Call this as early as possible, not from an import, and only once."""
	from qbroker import setup; setup(gevent=True)
	import gevent.monkey
	gevent.monkey.patch_all()

	import logging,sys
	logging.basicConfig(stream=sys.stderr,level=logging.DEBUG if TESTING else logging.WARN)

