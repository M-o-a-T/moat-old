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

"""List of known devices"""

import os
from ..script.util import objects

import logging
logger = logging.getLogger(__name__)

DEV_DIR = ('device',)
DEV = ':dev'

def devices():
	from .base import BaseDevice
	# we want all objects with a distinctive prefix
	return objects(__name__, BaseDevice, filter=lambda x:x.__dict__.get('prefix',None) is not None)

def setup_dev_types(types):
	"""Register types for all devices."""
	types = types.step(DEV_DIR)
	for dev in devices():
		t = types.step(dev.prefix)
		for p in dev.dev_paths():
			t.step(p[:-1]).register(DEV, cls=p[-1])

	from .base import DeadDevice
	types.register('**',DEV, cls=DeadDevice)

