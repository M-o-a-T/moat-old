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

"""Helper code for scripting"""

from importlib import import_module
import pkgutil

import logging
logger = logging.getLogger(__name__)

def objects(module, cls, immediate=False,direct=False,filter=lambda x:True):
	"""\
		List all objects of a given class in a directory.

		If @immediate is set, only direct subclasses are returned.
		If @direct is set, modules in subdirectories are ignored.
		"""
	if isinstance(module,str):
		from dabroker.util import import_string
		module = import_string(module)
	for a,b,c in pkgutil.walk_packages(module.__path__, module.__name__+'.'):
		if direct and a.path != module.__path__[0]:
			continue
		try:
			m = import_module(b)
		except ImportError as ex:
			raise ImportError(b) from ex # pragma: no cover
			# not going to ship a broken file for testing this
		else:
			try:
				syms = m.__all__
			except AttributeError:
				syms = dir(m)
			for c in syms:
				c = getattr(m,c,None)
				if isinstance(c,type) and \
						((c.__base__ is cls) if immediate else (c is not cls and issubclass(c,cls))):
					if filter(c):
						yield c
			
