# -*- coding: utf-8 -*-

## 
##  Copyright © 2007-2012, Matthias Urlichs <matthias@urlichs.de>
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

"""\
This is the core of the event dispatcher.
"""

from __future__ import division,absolute_import

import os

VERSION = "0.4"

TESTING = "MOAT_TEST" in os.environ

	# This test is also in moat/twist.py, for recursive-import reasons

def patch():
	"""Call this as early as possible, not from an import, and only once."""
	from dabroker import patch; patch()
	try:
		from moat.gevent_rpyc import patch_all; patch_all()
	except ImportError:
		pass

	import logging,sys
	logging.basicConfig(stream=sys.stderr,level=logging.DEBUG if TESTING else logging.WARN)


