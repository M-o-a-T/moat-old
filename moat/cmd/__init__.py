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

"""List of known Tasks"""

import os
from dabroker.util import import_string
from ..script import Command

import logging
logger = logging.getLogger(__name__)

def commands():
	for m in __path__:
		for p in os.listdir(m):
			if p[0] == '.':
				continue # pragma: no cover
			if p[0] == '_':
				continue
			if p.endswith('.py') or '.' not in p:
				if p.endswith('.py'):
					p = p[:-3]
				try:
					m = import_string(__name__+'.'+p)
				except ImportError:
					logger.exception("Trying to import "+__name__+'.'+p) # pragma: no cover
					# not going to ship a broken file for testing this
				else:
					try:
						syms = (getattr(m,s,None) for s in m.__all__)
					except AttributeError:
						syms = m.__dict__.values()
					for c in syms:
						if isinstance(c,type) and c is not Command and issubclass(c,Command):
							yield c
					
